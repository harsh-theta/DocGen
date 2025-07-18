import { useState } from "react";
import { Box, Button, FormControl, FormLabel, Input, Heading, Text, Alert, AlertIcon } from "@chakra-ui/react";

type AuthMode = "login" | "register";

interface AuthFormProps {
  mode: AuthMode;
  onSubmit: (email: string, password: string) => Promise<void>;
  loading?: boolean;
  error?: string;
}

const AuthForm = ({ mode, onSubmit, loading, error }: AuthFormProps) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(email, password);
  };

  return (
    <Box maxW="sm" mx="auto" mt={16} p={8} borderWidth={1} borderRadius="lg" boxShadow="md" bg="white">
      <Heading as="h2" size="lg" mb={6} textAlign="center">
        {mode === "login" ? "Login" : "Register"}
      </Heading>
      {error && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          {error}
        </Alert>
      )}
      <form onSubmit={handleSubmit}>
        <FormControl id="email" mb={4} isRequired>
          <FormLabel>Email</FormLabel>
          <Input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            autoComplete="email"
          />
        </FormControl>
        <FormControl id="password" mb={6} isRequired>
          <FormLabel>Password</FormLabel>
          <Input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </FormControl>
        <Button type="submit" colorScheme="teal" width="full" isLoading={loading}>
          {mode === "login" ? "Login" : "Register"}
        </Button>
      </form>
    </Box>
  );
};

export default AuthForm; 