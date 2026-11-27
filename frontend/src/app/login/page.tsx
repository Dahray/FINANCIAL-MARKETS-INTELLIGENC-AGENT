"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, ShieldCheck } from "lucide-react";
import { fmipApi } from "@/lib/api";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components/ui/primitives";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@sohcahtoaholdings.com");
  const [password, setPassword] = useState("SohCahToa@Admin2026!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await fmipApi.login(email, password);
      router.push("/overview");
    } catch (err: any) {
      setError(
        err?.message ||
          "Unable to reach FastAPI auth server at localhost:8000. Ensure backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-950 p-6">
      <Card className="w-full max-w-md border-orange-500/40">
        <CardHeader className="space-y-2">
          <div className="flex items-center justify-between">
            <Badge variant="orange">SOHCAHTOA INSTITUTIONAL AUTH</Badge>
            <span className="font-mono text-xs text-stone-400">JWT / PBKDF2-SHA256</span>
          </div>
          <CardTitle className="text-lg">
            SohCahToa Financial Markets Intelligence Platform
          </CardTitle>
          <p className="text-xs text-stone-400">
            Sign in to access Nigerian, African & Global Financial Intelligence, Opportunity Radar, and Friday Executive Reports.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-stone-300 mb-1">
                Institutional Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-stone-700 bg-stone-900 px-3 py-2 text-sm text-white focus:border-orange-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-300 mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-stone-700 bg-stone-900 px-3 py-2 text-sm text-white focus:border-orange-500 focus:outline-none"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-rose-700/60 bg-rose-950/60 p-3 text-xs text-rose-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-orange-600 hover:bg-orange-500 disabled:opacity-50 px-4 py-2.5 text-sm font-semibold text-white transition-colors shadow-sm shadow-orange-600/30"
            >
              <Lock className="h-4 w-4" />
              {loading ? "Authenticating..." : "Sign In to Research Terminal"}
            </button>

            <div className="pt-2 border-t border-stone-800/80 flex items-center justify-between text-xs text-stone-400">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-orange-400" />
                Audit Logging Enabled
              </span>
              <button
                type="button"
                onClick={() => router.push("/overview")}
                className="text-orange-400 hover:underline"
              >
                Continue to Dashboard →
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
