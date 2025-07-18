import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import DocumentList, { DocumentItem } from "../components/DocumentList";
import { Heading, Box, Spinner, Alert, AlertIcon } from "@chakra-ui/react";
import axios from "axios";

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDocuments = async () => {
      setLoading(true);
      setError("");
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        // TODO: Replace with real API endpoint
        const response = await axios.get(
          process.env.NEXT_PUBLIC_API_URL + "/documents" || "http://localhost:8000/documents",
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }
        );
        // Map backend data to DocumentItem[]
        setDocuments(
          response.data.map((doc: any) => ({
            id: doc.id,
            name: doc.name || doc.original_file_url?.split("/").pop() || "Untitled",
            createdAt: doc.created_at,
            type: doc.ai_content ? "generated" : "original",
            status: doc.status || (doc.ai_content ? "Generated" : "Uploaded"),
            url: doc.final_file_url || doc.original_file_url,
          }))
        );
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load documents.");
      } finally {
        setLoading(false);
      }
    };
    fetchDocuments();
  }, []);

  return (
    <Layout>
      <Box maxW="4xl" mx="auto" mt={10}>
        <Heading mb={6}>Your Documents</Heading>
        {loading ? (
          <Spinner size="lg" />
        ) : error ? (
          <Alert status="error" mb={4}>
            <AlertIcon />
            {error}
          </Alert>
        ) : (
          <DocumentList documents={documents} />
        )}
      </Box>
    </Layout>
  );
} 