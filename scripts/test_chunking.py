"""Self-contained chunking test — no Docker or external services needed.

Creates sample documents, runs the full chunking pipeline, and writes
results to a txt file for inspection.
"""

import os
import sys
import json
import uuid
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.chunker import RecursiveTextChunker, TextChunk
from app.ingestion.parser import DocumentParser, ParsedDocument


# ─── Sample Documents ───────────────────────────────────────────────────────

SAMPLE_DOCUMENTS = [
    {
        "filename": "company_policy.txt",
        "file_type": "txt",
        "content": """Company Refund Policy

1. Overview
Our company is committed to customer satisfaction. If you are not satisfied with your purchase, we offer refunds within 30 days of the original purchase date.

2. Eligibility
To be eligible for a refund, you must meet the following criteria:
- The item must be in its original condition
- You must provide proof of purchase (receipt or order number)
- The request must be made within 30 days of purchase

3. Process
To request a refund, please contact our customer support team at support@company.com or call 1-800-123-4567. Please have your order number ready.

4. Timeline
Refunds are processed within 5-7 business days after we receive your returned item. The refund will be issued to your original payment method.

5. Exceptions
The following items are not eligible for refunds:
- Gift cards
- Downloadable software
- Items marked as final sale
- Personalized or custom items

6. Shipping Costs
Original shipping costs are non-refundable. Return shipping costs are the responsibility of the customer unless the return is due to our error.

7. Damaged or Defective Items
If you received a damaged or defective item, please contact us within 7 days of delivery. We will arrange for a replacement or full refund including shipping costs.

8. Contact Information
For any questions about our refund policy, please reach out to:
- Email: support@company.com
- Phone: 1-800-123-4567
- Address: 123 Business St, Suite 100, City, ST 12345""",
    },
    {
        "filename": "product_manual.txt",
        "file_type": "txt",
        "content": """Product User Manual — Model X100

Chapter 1: Getting Started
Thank you for purchasing the X100. This manual will help you set up and use your new device.

1.1 Unboxing
Your X100 package contains:
- 1x X100 device
- 1x USB-C charging cable
- 1x Power adapter
- 1x Quick start guide
- 1x Warranty card

1.2 Charging
Before first use, charge your X100 for at least 2 hours. Connect the USB-C cable to the device and plug the power adapter into a wall outlet. The LED indicator will turn green when fully charged.

1.3 Power On
Press and hold the power button for 3 seconds to turn on the device. The welcome screen will appear.

Chapter 2: Basic Operations

2.1 Navigation
The X100 features a 5-inch touchscreen. Swipe left or right to navigate between screens. Tap to select an item. Pinch to zoom in or out.

2.2 Settings
Access settings by tapping the gear icon on the home screen. From here you can adjust:
- Display brightness
- Volume
- Language
- Date and time
- Network settings

2.3 Connecting to Wi-Fi
Go to Settings > Network > Wi-Fi. Select your network from the list and enter the password. The X100 supports 2.4GHz and 5GHz networks.

Chapter 3: Troubleshooting

3.1 Device Won't Turn On
- Ensure the device is charged
- Try holding the power button for 10 seconds
- Check that the charging cable is properly connected

3.2 Screen is Frozen
- Press and hold the power button for 15 seconds to force restart
- If the problem persists, contact technical support

3.3 Wi-Fi Connection Issues
- Restart your router
- Forget the network and reconnect
- Move closer to the router
- Check if other devices can connect

Chapter 4: Maintenance

4.1 Cleaning
Use a soft, dry cloth to clean the screen. Do not use abrasive cleaners or solvents.

4.2 Battery Care
To maximize battery life:
- Avoid extreme temperatures
- Charge before the battery drops below 10%
- Use only the provided charger

4.3 Software Updates
The X100 will automatically check for updates when connected to Wi-Fi. You can also manually check in Settings > System > Updates.

Chapter 5: Warranty

5.1 Warranty Coverage
The X100 comes with a 2-year limited warranty covering manufacturing defects. This warranty does not cover:
- Accidental damage
- Water damage
- Unauthorized modifications
- Normal wear and tear

5.2 Warranty Claims
To make a warranty claim, contact support@company.com with your proof of purchase and a description of the issue.""",
    },
    {
        "filename": "faq.txt",
        "file_type": "txt",
        "content": """Frequently Asked Questions — Company Services

Q: What are your business hours?
A: Our offices are open Monday through Friday, 9:00 AM to 6:00 PM EST. Customer support is available 24/7 via email.

Q: How do I track my order?
A: Once your order ships, you will receive an email with a tracking number. You can also log into your account on our website to view order status.

Q: Do you offer international shipping?
A: Yes, we ship to over 50 countries. International shipping typically takes 7-14 business days. Customs fees and import duties are the responsibility of the customer.

Q: Can I change or cancel my order?
A: Orders can be modified or cancelled within 2 hours of placement. After that, orders enter our fulfillment process and cannot be changed.

Q: What payment methods do you accept?
A: We accept Visa, MasterCard, American Express, Discover, PayPal, and Apple Pay. We do not accept checks or money orders.

Q: How do I create an account?
A: Click the "Sign Up" button on our homepage. You will need to provide your name, email address, and create a password. Account creation is free.

Q: Is my personal information secure?
A: Yes. We use industry-standard SSL encryption to protect your data. We never sell or share your personal information with third parties.

Q: Do you offer bulk or corporate discounts?
A: Yes, we offer volume discounts for orders of 50 units or more. Please contact our sales team at sales@company.com for a custom quote.

Q: What is your return policy for opened items?
A: Opened items can be returned within 15 days for a partial refund (80% of purchase price). Items must be in resalable condition with all original packaging.

Q: How do I contact technical support?
A: For technical issues, email techsupport@company.com or call 1-800-123-4567 ext. 2. Our technical team responds within 4 business hours.""",
    },
]


# ─── Mock Embedder (no OpenAI API needed) ────────────────────────────────────

class MockEmbedder:
    """Generate deterministic pseudo-embeddings for testing."""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        """Generate a deterministic embedding based on text content."""
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        embedding = []
        for i in range(self.dimensions):
            hash_val = (hash_val * 1103515245 + 12345 + i) & 0x7FFFFFFF
            embedding.append((hash_val / 0x7FFFFFFF) * 2 - 1)
        return embedding

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        return [self.embed_text(text) for text in texts]


# ─── Main Test ───────────────────────────────────────────────────────────────

def run_chunking_test(file_path: str = None):
    """Run the full chunking pipeline and write results to a txt file."""

    if file_path:
        # Chunk a single real file instead of the sample documents
        import os
        parser = DocumentParser()
        ext = os.path.splitext(file_path)[1].lstrip(".").lower()
        parsed = parser.parse(file_path, ext)
        documents = [{
            "filename": os.path.basename(file_path),
            "file_type": ext,
            "content": parsed.text,
            "pages": parsed.pages,
        }]
    else:
        documents = [dict(d, pages=[]) for d in SAMPLE_DOCUMENTS]

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"chunking_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    chunker = RecursiveTextChunker(chunk_size=200, chunk_overlap=30)
    embedder = MockEmbedder(dimensions=1536)

    all_chunks = []
    all_embeddings = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("CHUNKING PIPELINE TEST RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Chunk Size: 200 tokens\n")
        f.write(f"Chunk Overlap: 30 tokens\n")
        f.write(f"Embedding Dimensions: 1536 (mock)\n")
        f.write(f"Documents Processed: {len(documents)}\n")
        f.write("=" * 80 + "\n\n")

        total_chunks = 0

        for doc_idx, doc_data in enumerate(documents):
            filename = doc_data["filename"]
            content = doc_data["content"]

            f.write(f"\n{'─' * 80}\n")
            f.write(f"DOCUMENT {doc_idx + 1}: {filename}\n")
            f.write(f"{'─' * 80}\n")
            f.write(f"File Type: {doc_data['file_type']}\n")
            f.write(f"Content Length: {len(content)} characters\n")
            f.write(f"Content Lines: {len(content.splitlines())}\n\n")

            # Parse (simulated — text is already extracted)
            parsed = ParsedDocument(
                text=content,
                pages=doc_data["pages"] or [content],
                metadata={"source": "test"},
            )

            # Chunk
            chunks = chunker.chunk_text(parsed.text, parsed.pages)

            f.write(f"CHUNKS CREATED: {len(chunks)}\n\n")

            for i, chunk in enumerate(chunks):
                total_chunks += 1
                embedding = embedder.embed_text(chunk.text)

                all_chunks.append({
                    "id": str(uuid.uuid4()),
                    "document": filename,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "page_number": chunk.page_number,
                    "embedding_preview": embedding[:10],
                })
                all_embeddings.append(embedding)

                f.write(f"  ┌─ Chunk {i + 1} (Index: {chunk.chunk_index}) ─{'─' * 40}\n")
                f.write(f"  │ Tokens: {chunk.token_count}\n")
                f.write(f"  │ Page: {chunk.page_number or 'N/A'}\n")
                f.write(f"  │ Embedding (first 10): {[round(x, 4) for x in embedding[:10]]}\n")
                f.write(f"  │\n")
                # Write text with indentation
                text_lines = chunk.text.split("\n")
                for line in text_lines[:5]:
                    f.write(f"  │ {line}\n")
                if len(text_lines) > 5:
                    f.write(f"  │ ... ({len(text_lines) - 5} more lines)\n")
                f.write(f"  └{'─' * 60}\n\n")

        # Summary
        f.write(f"\n{'=' * 80}\n")
        f.write("SUMMARY\n")
        f.write(f"{'=' * 80}\n")
        f.write(f"Total Documents: {len(documents)}\n")
        f.write(f"Total Chunks Created: {total_chunks}\n")
        f.write(f"Average Chunks per Document: {total_chunks / len(documents):.1f}\n")
        f.write(f"Embedding Dimensions: 1536\n")
        f.write(f"Total Embeddings Generated: {len(all_embeddings)}\n")
        f.write(f"\nChunk Distribution:\n")

        for doc_data in documents:
            doc_chunks = [c for c in all_chunks if c["document"] == doc_data["filename"]]
            f.write(f"  {doc_data['filename']}: {len(doc_chunks)} chunks\n")

        f.write(f"\n{'=' * 80}\n")
        f.write("END OF CHUNKING TEST\n")
        f.write(f"{'=' * 80}\n")

    print(f"\nChunking test complete!")
    print(f"Total chunks created: {total_chunks}")
    print(f"Results saved to: {output_file}")
    print(f"\nTo view results:")
    print(f"  notepad {output_file}")
    print(f"  type {output_file}")

    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the chunking pipeline")
    parser.add_argument("file", nargs="?", help="Optional real file to chunk instead of sample documents")
    args = parser.parse_args()

    print("\n" + "#" * 80)
    print("# CHUNKING PIPELINE TEST")
    print("#" * 80)
    print("\nThis test creates sample documents and runs the chunking pipeline.")
    print("No Docker or external services required.\n")

    output = run_chunking_test(file_path=args.file)

    print("\n" + "#" * 80)
    print("# TEST COMPLETE")
    print("#" * 80)
