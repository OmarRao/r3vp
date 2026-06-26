import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { UserProvider } from "@auth0/nextjs-auth0/client";
import { QueryProvider } from "@/components/query-provider";
import { FirebaseInit } from "@/components/firebase-init";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "R3VP — Recovery Validation Platform",
  description: "Prove your ransomware recovery works before you need it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <UserProvider>
          <FirebaseInit />
          <QueryProvider>{children}</QueryProvider>
        </UserProvider>
      </body>
    </html>
  );
}
