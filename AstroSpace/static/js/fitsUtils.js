
export async function readXISFHeader(file) {
    const signatureLength = 8;        // "XISF0100" etc.
    const headerLengthField = 4;      // uint32 little-endian
    const reservedLength = 56;        // standard XISF

    // Read the initial bytes to determine header size
    const initialSize = signatureLength + headerLengthField + reservedLength;
    let initialChunk = await file.slice(0, initialSize).arrayBuffer();
    let dataView = new DataView(initialChunk);

    // Read header length (starts immediately after signature)
    const headerLength = dataView.getUint32(signatureLength, true);

    if (headerLength > MAX_HEADER_SIZE) {
        throw new Error("XISF header is unreasonably large (>5 MB)");
    }

    // Now read the header itself
    const headerStart = initialSize;
    const headerEnd = headerStart + headerLength;

    let headerChunk = await file.slice(headerStart, headerEnd).arrayBuffer();
    return new Uint8Array(headerChunk);
}

export async function readFITSHeader(file) {
    const CHUNK = 2880;
    const CARD = 80;
    const MAX_HEADER_SIZE = 500 * 1024;

    let offset = 0;
    let collected = [];

    while (true) {
        if (offset >= MAX_HEADER_SIZE) {
            throw new Error("FITS header is unreasonably large (>5 MB)");
        }

        const buffer = await file.slice(offset, offset + CHUNK).arrayBuffer();
        const text = new TextDecoder("ascii").decode(buffer);

        for (let i = 0; i < text.length; i += CARD) {
            const card = text.slice(i, i + CARD);
            collected.push(card);

            if (card.startsWith("END")) {
                const headerText = collected.join("");
                return new Uint8Array(
                    new TextEncoder().encode(headerText)
                );
            }
        }

        offset += CHUNK;
    }
}
