/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  extends: ['@crewai/eslint-config/next.js'],
  parserOptions: {
    project: './tsconfig.json',
  },
};