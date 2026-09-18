import type { StorybookConfig } from '@storybook/react-vite'

function withoutPwa(plugins: any[]): any[] {
  return plugins.flatMap((plugin) => {
    if (Array.isArray(plugin)) return withoutPwa(plugin)
    const name = plugin && typeof plugin === 'object' ? String(plugin.name ?? '') : ''
    return name.includes('vite-plugin-pwa') ? [] : [plugin]
  })
}

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  addons: ['@storybook/addon-a11y'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: { autodocs: 'tag' },
  viteFinal: async (viteConfig) => ({
    ...viteConfig,
    plugins: withoutPwa((viteConfig.plugins ?? []) as any[]),
  }),
}

export default config
