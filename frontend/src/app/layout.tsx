import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SohCahToa FMIP — AI Financial Markets Intelligence Platform",
  description:
    "Institutional AI-Powered Financial Markets, Macroeconomic, Quantitative, Competitive, Regulatory, and Strategic Intelligence Platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className="min-h-screen bg-stone-950 text-stone-100 antialiased"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
