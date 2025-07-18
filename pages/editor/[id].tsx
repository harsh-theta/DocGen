import { useRouter } from "next/router";
import { useEffect, useState, useCallback } from "react";
import Layout from "../../components/Layout";
import Editor from "../../components/Editor";
import { Box, Heading, Spinner, Alert, AlertIcon, Button, Text } from "@chakra-ui/react";
import axios from "axios";

function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

export default function DocumentEditorPage() {
  const router = useRouter();
  const { id } = router.query;
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchDoc = async () => {
      setLoading(true);
      setError("");
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        // TODO: Replace with real API endpoint
        const response = await axios.get(
          process.env.NEXT_PUBLIC_API_URL + `/session/${id}` || `http://localhost:8000/session/${id}`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }
        );
        setContent(response.data.ai_content || response.data.parsed_structure || "");
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load document.");
      } finally {
        setLoading(false);
      }
    };
    fetchDoc();
  }, [id]);

  // Debounced save
  const saveContent = useCallback(
    debounce(async (newContent: string) => {
      if (!id) return;
      setSaving(true);
      setSaveSuccess(false);
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        await axios.post(
          process.env.NEXT_PUBLIC_API_URL + "/save-edits" || "http://localhost:8000/save-edits",
          { id, content: newContent },
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }
        );
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 1500);
      } catch (err) {
        // Optionally handle error
      } finally {
        setSaving(false);
      }
    }, 1000),
    [id]
  );

  const handleChange = (newContent: string) => {
    setContent(newContent);
    saveContent(newContent);
  };

  return (
    <Layout>
      <Box maxW="4xl" mx="auto" mt={10}>
        <Heading mb={6}>Edit Document</Heading>
        {loading ? (
          <Spinner size="lg" />
        ) : error ? (
          <Alert status="error" mb={4}>
            <AlertIcon />
            {error}
          </Alert>
        ) : (
          <>
            <Editor initialContent={content} onChange={handleChange} loading={saving} />
            {saveSuccess && (
              <Text color="green.500" mt={2}>Saved!</Text>
            )}
          </>
        )}
      </Box>
    </Layout>
  );
} 