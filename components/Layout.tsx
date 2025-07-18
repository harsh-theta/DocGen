import { ReactNode } from "react";
import { Box, Container } from "@chakra-ui/react";

interface LayoutProps {
  children: ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <Box minH="100vh" bg="gray.50">
      <Container maxW="container.lg" py={8}>
        {children}
      </Container>
    </Box>
  );
};

export default Layout; 