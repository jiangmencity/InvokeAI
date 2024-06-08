from functools import singledispatchmethod

import einops
import torch
from diffusers.models.attention_processor import (
    AttnProcessor2_0,
    LoRAAttnProcessor2_0,
    LoRAXFormersAttnProcessor,
    XFormersAttnProcessor,
)
from diffusers.models.autoencoders.autoencoder_kl import AutoencoderKL
from diffusers.models.autoencoders.autoencoder_tiny import AutoencoderTiny

from invokeai.app.invocations.baseinvocation import BaseInvocation, invocation
from invokeai.app.invocations.denoise_latents import DEFAULT_PRECISION
from invokeai.app.invocations.fields import (
    FieldDescriptions,
    ImageField,
    Input,
    InputField,
)
from invokeai.app.invocations.model import VAEField
from invokeai.app.invocations.primitives import LatentsOutput
from invokeai.app.services.shared.invocation_context import InvocationContext
from invokeai.backend.model_manager import LoadedModel
from invokeai.backend.stable_diffusion.diffusers_pipeline import image_resized_to_grid_as_tensor


@invocation(
    "i2l",
    title="Image to Latents",
    tags=["latents", "image", "vae", "i2l"],
    category="latents",
    version="1.0.2",
)
class ImageToLatentsInvocation(BaseInvocation):
    """Encodes an image into latents."""

    image: ImageField = InputField(
        description="The image to encode",
    )
    vae: VAEField = InputField(
        description=FieldDescriptions.vae,
        input=Input.Connection,
    )
    tiled: bool = InputField(default=False, description=FieldDescriptions.tiled)
    fp32: bool = InputField(default=DEFAULT_PRECISION == "float32", description=FieldDescriptions.fp32)

    @staticmethod
    def vae_encode(vae_info: LoadedModel, upcast: bool, tiled: bool, image_tensor: torch.Tensor) -> torch.Tensor:
        with vae_info as vae:
            assert isinstance(vae, torch.nn.Module)
            orig_dtype = vae.dtype
            if upcast:
                vae.to(dtype=torch.float32)

                use_torch_2_0_or_xformers = hasattr(vae.decoder, "mid_block") and isinstance(
                    vae.decoder.mid_block.attentions[0].processor,
                    (
                        AttnProcessor2_0,
                        XFormersAttnProcessor,
                        LoRAXFormersAttnProcessor,
                        LoRAAttnProcessor2_0,
                    ),
                )
                # if xformers or torch_2_0 is used attention block does not need
                # to be in float32 which can save lots of memory
                if use_torch_2_0_or_xformers:
                    vae.post_quant_conv.to(orig_dtype)
                    vae.decoder.conv_in.to(orig_dtype)
                    vae.decoder.mid_block.to(orig_dtype)
                # else:
                #    latents = latents.float()

            else:
                vae.to(dtype=torch.float16)
                # latents = latents.half()

            if tiled:
                vae.enable_tiling()
            else:
                vae.disable_tiling()

            # non_noised_latents_from_image
            image_tensor = image_tensor.to(device=vae.device, dtype=vae.dtype)
            with torch.inference_mode():
                latents = ImageToLatentsInvocation._encode_to_tensor(vae, image_tensor)

            latents = vae.config.scaling_factor * latents
            latents = latents.to(dtype=orig_dtype)

        return latents

    @torch.no_grad()
    def invoke(self, context: InvocationContext) -> LatentsOutput:
        image = context.images.get_pil(self.image.image_name)

        vae_info = context.models.load(self.vae.vae)

        image_tensor = image_resized_to_grid_as_tensor(image.convert("RGB"))
        if image_tensor.dim() == 3:
            image_tensor = einops.rearrange(image_tensor, "c h w -> 1 c h w")

        latents = self.vae_encode(vae_info, self.fp32, self.tiled, image_tensor)

        latents = latents.to("cpu")
        name = context.tensors.save(tensor=latents)
        return LatentsOutput.build(latents_name=name, latents=latents, seed=None)

    @singledispatchmethod
    @staticmethod
    def _encode_to_tensor(vae: AutoencoderKL, image_tensor: torch.FloatTensor) -> torch.FloatTensor:
        assert isinstance(vae, torch.nn.Module)
        image_tensor_dist = vae.encode(image_tensor).latent_dist
        latents: torch.Tensor = image_tensor_dist.sample().to(
            dtype=vae.dtype
        )  # FIXME: uses torch.randn. make reproducible!
        return latents

    @_encode_to_tensor.register
    @staticmethod
    def _(vae: AutoencoderTiny, image_tensor: torch.FloatTensor) -> torch.FloatTensor:
        assert isinstance(vae, torch.nn.Module)
        latents: torch.FloatTensor = vae.encode(image_tensor).latents
        return latents
