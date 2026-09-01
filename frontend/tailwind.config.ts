const config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--bg)",
        border: "var(--border)",
        foreground: "var(--text)",
        muted: "var(--text-muted)",
        surface: "var(--surface)",
      },
    },
  },
  plugins: [],
};

export default config;
