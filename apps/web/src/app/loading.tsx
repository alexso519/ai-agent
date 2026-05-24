export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}