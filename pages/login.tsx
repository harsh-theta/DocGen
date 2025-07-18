import { useState } from "react";
import AuthForm from "../components/AuthForm";
import Layout from "../components/Layout";
import { useRouter } from "next/router";
import { login as loginApi } from "../utils/api";
import { Box, Text, Link as ChakraLink } from "@chakra-ui/react";
import NextLink from "next/link";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleLogin = async (email: string, password: string) => {
    setLoading(true);
    setError("");
    try {
      const data = await loginApi(email, password);
      if (data && data.token) {
        localStorage.setItem("token", data.token);
        router.push("/dashboard");
      } else {
        setError(data?.detail || "Login failed. Please try again.");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <AuthForm mode="login" onSubmit={handleLogin} loading={loading} error={error} />
      <Box textAlign="center" mt={4}>
        <Text>
          New here?{' '}
          <NextLink href="/register" passHref legacyBehavior>
            <ChakraLink color="teal.500">Create an account</ChakraLink>
          </NextLink>
        </Text>
      </Box>
    </Layout>
  );
} 