import { ChakraProvider } from "@chakra-ui/react";
import { SaasProvider } from "@saas-ui/react";
import type { AppProps } from "next/app";

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ChakraProvider>
      <SaasProvider>
        <Component {...pageProps} />
      </SaasProvider>
    </ChakraProvider>
  );
}

export default MyApp; 