This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

## 1st: deploy the AI model
Download the AI model from [here](https://huggingface.co/TWKrito/interview_simulate/tree/main)
After downloading the model. Create a new folder in (..\AI_Career_Coach) named 'models' and put the file just downloaded in it.

Then donwload Ollama from [here](https://ollama.com/download) and install it. 
Run the following command in file path (..\AI_Career_Coach\models) to import the model to PC:
```bash
ollama create my-career-coach -f Modelfile
```

## 2nd, install the dependencies:
```bash
npm install
```

## 3rd, run the development server:
Backend(launch cmd in ..\AI_Career_Coach):

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```
Frontend(launch cmd in ..\AI_Career_Coach\frontend):

```bush
uvicorn Main:app --reload --port 8000
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
