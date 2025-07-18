import { useState } from "react";
import UploadForm from "../components/UploadForm";
import Layout from "../components/Layout";
import { Box, Text } from "@chakra-ui/react";
import axios from "axios";

export default function UploadPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleUpload = async (file: File) => {
    setLoading(true);
    setError("");
    setSuccess(false);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      await axios.post(
        process.env.NEXT_PUBLIC_API_URL + "/upload-doc" || "http://localhost:8000/upload-doc",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        }
      );
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <UploadForm onSubmit={handleUpload} loading={loading} error={error} />
      {success && (
        <Box textAlign="center" mt={4}>
          <Text color="green.500">File uploaded successfully!</Text>
        </Box>
      )}
    </Layout>
  );
} 