export default {
  extends: ['stylelint-config-standard'],
  ignoreFiles: ['node_modules/**', 'artifacts/**', 'build/**', 'dist/**'],
  rules: {
    'selector-class-pattern': null,
    'custom-property-pattern': null,
  },
};
