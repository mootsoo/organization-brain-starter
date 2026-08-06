import "./globals.css";

export const metadata = {
  title: "Байгууллагын тархи",
  description:
    "Батлагдсан өгөгдөл, тодорхой дүрэм, AI-аар бэлтгэсэн төсөл, хүний шийдвэрийг нэг урсгалд холбосон энгийн жишиг систем.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="mn">
      <body>{children}</body>
    </html>
  );
}
