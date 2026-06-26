'use client'

import QueryProvider from '../lib/providers/queryClientProvider'

export default function Providers({ children }: { children: React.ReactNode }) {
    return (
        <QueryProvider>
            {/* <ThemeProvider> */}
            {/* <AuthProvider> */}
            {children}
            {/* </AuthProvider> */}
            {/* </ThemeProvider> */}
        </QueryProvider>
    )
}