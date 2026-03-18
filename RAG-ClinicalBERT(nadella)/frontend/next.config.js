/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:5557/api/:path*',
            },
            {
                source: '/login',
                destination: 'http://localhost:5557/login',
            },
            {
                source: '/logout',
                destination: 'http://localhost:5557/logout',
            }
        ]
    },
}

module.exports = nextConfig
