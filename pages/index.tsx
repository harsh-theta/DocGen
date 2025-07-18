import { Box, Heading, Text, Button } from "@chakra-ui/react";
import Layout from "../components/Layout";

export default function Home() {
  return (
    <Layout>
      <Box textAlign="center" mt={20}>
        <Heading as="h1" size="2xl" mb={4}>
          🧠 DocGen
        </Heading>
        <Text fontSize="xl" mb={8}>
          AI-powered document generation system
        </Text>
        <Button colorScheme="teal" size="lg">
          Get Started
        </Button>
      </Box>
    </Layout>
  );
} 