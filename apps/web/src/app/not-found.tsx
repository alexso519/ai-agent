import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4">
      <h2 className="text-lg font-semibold text-slate-800">Page not found</h2>
      <p className="text-sm text-slate-500">Could not find the requested resource</p>
      <Link
        href="/"
        className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
      >
        Return Home
      </Link>
    </div>
  );
}