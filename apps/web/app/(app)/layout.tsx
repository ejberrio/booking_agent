import { Sidebar } from "@/components/layout/sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="px-4 pb-6 pt-16 md:ml-56 md:px-8 md:pt-6">{children}</main>
    </div>
  );
}
