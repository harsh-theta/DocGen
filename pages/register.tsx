import { useState } from "react";
import AuthForm from "../components/AuthForm";
import Layout from "../components/Layout";
import { useRouter } from "next/router";
import { register as registerApi } from "../utils/api";
import { Box, Text, Link as ChakraLink } from "@chakra-ui/react";
import NextLink from "next/link";

export default function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleRegister = async (email: string, password: string) => {
    setLoading(true);
    setError("");
    try {
      await registerApi(email, password);
      router.push("/login");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <AuthForm mode="register" onSubmit={handleRegister} loading={loading} error={error} />
      <Box textAlign="center" mt={4}>
        <Text>
          Already have an account?{' '}
          <NextLink href="/login" passHref legacyBehavior>
            <ChakraLink color="teal.500">Login</ChakraLink>
          </NextLink>
        </Text>
      </Box>
    </Layout>
  );
} 