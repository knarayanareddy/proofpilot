import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// Software GL: this container has no GPU, and ANGLE/SwiftShader keeps canvas rendering stable.
Config.setChromiumOpenGlRenderer('swangle');
Config.setConcurrency(4);
Config.setCodec('h264');
Config.setCrf(20);
