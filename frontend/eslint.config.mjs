import tseslint from 'typescript-eslint'
import hooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
export default tseslint.config(
  {ignores: ['dist/**','node_modules/**','src/types/v1/*.generated.ts','test-results/**','playwright-report/**']},
  ...tseslint.configs.recommended,
  {files: ['src/**/*.{ts,tsx}'], languageOptions: {globals: globals.browser}, plugins: {'react-hooks':hooks}, rules: {'react-hooks/rules-of-hooks':'error'}},
  {files: ['*.mjs','e2e/**/*'], languageOptions: {globals: globals.node}},
)
