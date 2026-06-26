import { QueryClient } from '@tanstack/react-query'

export const queryClientConfig = {
    defaultOptions: {
        queries: {
            staleTime: 60 * 1000,
            retry: 1,
        },
    },
}

export const createQueryClient = () => new QueryClient(queryClientConfig)