import { defineConfig } from 'orval'

export default defineConfig({
  neginai: {
    input: { target: './neginai.openapi.json' },
    output: {
      target: './src/api/generated/neginApi.generated.ts',
      client: 'react-query',
      httpClient: 'fetch',
      mode: 'single',
      clean: true,
      override: {
        mutator: {
          path: './src/api/neginFetch.ts',
          name: 'neginFetch',
        },
      },
    },
  },
})
