import { Box, Flex } from '@invoke-ai/ui-library';
import { useStore } from '@nanostores/react';
import { overlayScrollbarsParams } from 'common/components/OverlayScrollbars/constants';
import { Prompts } from 'features/parameters/components/Prompts/Prompts';
import QueueControls from 'features/queue/components/QueueControls';
import { AdvancedSettingsAccordion } from 'features/settingsAccordions/components/AdvancedSettingsAccordion/AdvancedSettingsAccordion';
import { GenerationSettingsAccordion } from 'features/settingsAccordions/components/GenerationSettingsAccordion/GenerationSettingsAccordion';
import { UpscaleSettingsAccordion } from 'features/settingsAccordions/components/UpscaleSettingsAccordion/UpscaleSettingsAccordion';
import { StylePresetMenu } from 'features/stylePresets/components/StylePresetMenu';
import { StylePresetMenuTrigger } from 'features/stylePresets/components/StylePresetMenuTrigger';
import { $isMenuOpen } from 'features/stylePresets/store/isMenuOpen';
import { OverlayScrollbarsComponent } from 'overlayscrollbars-react';
import type { CSSProperties } from 'react';
import { memo } from 'react';

const overlayScrollbarsStyles: CSSProperties = {
  height: '100%',
  width: '100%',
};

const ParametersPanelUpscale = () => {
  const isMenuOpen = useStore($isMenuOpen);

  return (
    <Flex w="full" h="full" flexDir="column" gap={2}>
      <QueueControls />
      <StylePresetMenuTrigger />
      <Flex w="full" h="full" position="relative">
        <Box position="absolute" top={0} left={0} right={0} bottom={0}>
          {isMenuOpen && (
            <OverlayScrollbarsComponent defer style={overlayScrollbarsStyles} options={overlayScrollbarsParams.options}>
              <Flex gap={2} flexDirection="column" h="full" w="full">
                <StylePresetMenu />
              </Flex>
            </OverlayScrollbarsComponent>
          )}
          <OverlayScrollbarsComponent defer style={overlayScrollbarsStyles} options={overlayScrollbarsParams.options}>
            <Flex gap={2} flexDirection="column" h="full" w="full">
              <Prompts />
              <UpscaleSettingsAccordion />
              <GenerationSettingsAccordion />
              <AdvancedSettingsAccordion />
            </Flex>
          </OverlayScrollbarsComponent>
        </Box>
      </Flex>
    </Flex>
  );
};

export default memo(ParametersPanelUpscale);
