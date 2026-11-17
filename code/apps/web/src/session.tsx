import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Visibility, type Job } from "./api";

export const identities = [
  { token: "demo-amal", label: "Amal · Engineering" },
  { token: "demo-omar", label: "Omar · Engineering" },
  { token: "demo-nour", label: "Nour · Separate team" },
];
type Service = ReturnType<typeof api>;
const SessionContext = createContext<{ token: string; service: Service } | null>(null);

export function Session({ token, children }: { token: string; children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 600 } },
  }));
  const service = useMemo(() => api(token), [token]);
  return <QueryClientProvider client={client}>
    <SessionContext.Provider value={{ token, service }}>{children}</SessionContext.Provider>
  </QueryClientProvider>;
}

export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("Linkmind session unavailable");
  return session;
}

export function useViewer() {
  const { service } = useSession();
  return useQuery({ queryKey: ["viewer"], queryFn: service.me });
}

export function useGraph() {
  const { service } = useSession();
  return useQuery({ queryKey: ["graph"], queryFn: service.graph, refetchInterval: 1800 });
}

export function useJobs(document?: string) {
  const { service } = useSession();
  return useQuery({
    queryKey: document ? ["jobs", document] : ["jobs"], queryFn: () => document ? service.json<Job[]>("/sources?document_id=" + encodeURIComponent(document)) : service.jobs(),
    refetchInterval: (query) => query.state.data?.some((job) => ["queued", "processing"].includes(job.status)) ? 1000 : 5000,
  });
}

export function useIngest() {
  const { service } = useSession();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (source: { file: File; visibility: Visibility } | { sample: string; visibility: Visibility }) =>
      "file" in source ? service.upload(source.file, source.visibility) : service.sample(source.sample, source.visibility),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["jobs"] });
      void client.invalidateQueries({ queryKey: ["graph"] });
    },
  });
}
