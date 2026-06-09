import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import Link from 'next/link';
import NavbarStreak from '@/components/NavbarStreak';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'AMC 10 Trainer',
  description: 'Practice AMC 10 math competition problems',
};

function Navbar() {
  return (
    <nav className="h-12 shrink-0 bg-zinc-900 border-b border-zinc-800 flex items-center px-4 gap-6">
      <Link
        href="/"
        className="flex items-center gap-2 font-semibold text-zinc-100 text-sm hover:text-white transition-colors"
      >
        <span className="text-base">🧮</span>
        <span>AMC Trainer</span>
      </Link>
      <div className="h-4 w-px bg-zinc-700" />
      <Link
        href="/"
        className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
      >
        📚 Problems
      </Link>
      <Link
        href="/progress"
        className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
      >
        📊 Progress
      </Link>
      <Link
        href="/settings"
        className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
      >
        ⚙️ Settings
      </Link>
      <div className="ml-auto">
        <NavbarStreak />
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="h-full flex flex-col bg-zinc-950 text-zinc-100">
        <Navbar />
        <div className="flex-1 flex flex-col overflow-hidden">
          {children}
        </div>
      </body>
    </html>
  );
}
