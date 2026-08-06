import "./globals.css";

export const metadata = {
  title: "Байгууллагын тархи",
  description: "Өгөгдөл, дүрэм, AI туслах, хүний шийдвэрийг нэг урсгалд холбох жишиг систем.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="mn">
      <body>{children}</body>
    </html>
  );
}
