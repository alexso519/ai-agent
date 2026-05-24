import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CrewAI Enterprise Control Center',
  description: 'AI Operating System for Enterprise Workflow Orchestration',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}