import { FlatCompat } from "@eslint/eslintrc";
import { fileURLToPath } from "node:url";

const baseDirectory = fileURLToPath(new URL(".", import.meta.url));

const compat = new FlatCompat({ baseDirectory });

const eslintConfig = [
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      ".turbo/**",
      "next-env.d.ts",
      "tsconfig.tsbuildinfo",
    ],
  },
  ...compat.extends("next/core-web-vitals"),
  {
    rules: {
      // Generated media comes from provider/storage URLs that are not known at build time,
      // so next/image (which requires configured remotePatterns) cannot be used here.
      "@next/next/no-img-element": "off",
    },
  },
];

export default eslintConfig;
