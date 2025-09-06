import {defineConfig} from 'vite'
// import react from '@vitejs/plugin-react-swc'
import {resolve} from 'path'
// import tailwindcss from "@tailwindcss/vite";
// import autoprefixer from "autoprefixer";
import svgr from "vite-plugin-svgr";


export default defineConfig({
    // plugins: [react(),svgr()],
    plugins: [svgr()],
    css: {
        postcss: './postcss.config.js', // مسیر به فایل پیکربندی PostCSS
        // preprocessorOptions: {
        //     scss: {
        //         additionalData: `@import "./src/index.scss";` // مسیر گلوبال فایل SCSS
        //     }
        // }
    },
    // css: {
    //     preprocessorOptions: {
    //         scss: {
    //             additionalData: `@import "@/index.scss";` // مسیر گلوبال فایل SCSS
    //         }
    //     }
    // },
    base: "/static/",
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src') // تعریف alias برای src
        }
    },
    preview: {
        port: 5173,  // تغییر پورت به 4000
    },
    build: {
        server: {
            // host: 'localhost',
            port: 4173,
            // open: false,
            // watch: {
            //     usePolling: true,
            //     disableGlobbing: false,
            // },
            cors: true
        },
        manifest: "manifest.json",
        outDir: resolve("./static"),
        rollupOptions: {
            input: {
                main: 'src/main.jsx'
            }
        }
    }
})


// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react()],
// })