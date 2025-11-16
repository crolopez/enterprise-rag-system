# Web UI - Document Management

How to upload and manage documents through the Enterprise RAG Web UI.

## Supported Document Formats

The system supports a variety of document formats:

- **PDF** - `.pdf`
- **Text** - `.txt`
- **Word** - `.docx`
- **Markdown** - `.md`

## Upload Documents

### Via Open WebUI (Web Interface)

The easiest and most user-friendly method:

#### Step 1: Create a Knowledge Base

First, you need to create a Knowledge Base (a collection/folder where documents will be stored).

1. Open **http://localhost:3000** in your browser
2. On first access, you'll see a registration form (not login)
   - Enter any email and password - the first user becomes admin
   - Subsequent users will be regular users
3. In the **left sidebar**, click on **"Workspace"** (top icon with your initial)
4. Inside Workspace, click **"Knowledge"** or look for the **folder/document icon**
5. You should see a **"Create Knowledge Base"** button or **"+"** button
6. Click it and fill in:
   - **Name:** Something descriptive (e.g., `Company Docs`, `Research Papers`)
   - **Description:** Optional explanation (e.g., `Resume and career information`)
   - **Visibility:** Choose `Private` (recommended) or `Public`
7. Click **"Create"** to create the Knowledge Base

You now have an empty Knowledge Base ready for documents.

#### Step 2: Upload Documents to Your Knowledge Base

Now that your Knowledge Base is created, upload documents to it.

1. Click on your Knowledge Base name to **open it**
2. Inside the Knowledge Base, click the **"+"** button or **"Upload Documents"** button
3. Choose how to upload:
   - **Drag & Drop**: Drag files directly into the upload area
   - **Browse Files**: Click and select files from your computer
   - **Upload Multiple**: Hold `Ctrl` (Windows/Linux) or `Cmd` (macOS) to select multiple files
4. Select your documents:
   - **Supported formats:** PDF, TXT, DOCX, XLSX, PPTX, MD, JSON, CSV
   - **Recommended:** Files <100MB each for faster processing
5. Click **"Upload"** to start the indexing process

#### Step 3: Wait for Indexing to Complete

Documents are automatically embedded and indexed:

1. You'll see a progress indicator in your Knowledge Base
2. Indexing time depends on document size:
   - Small documents (<1MB): Usually complete within seconds
   - Large documents (10-100MB): May take 1-5 minutes
3. Once all documents show as "Indexed" or "Ready", they're available for search
4. You can check the Qdrant collection at **http://localhost:6333/dashboard** (optional)

#### Step 4: Use Documents in Chat (Select Your Knowledge Base)

Once documents are indexed, use them in a chat conversation.

1. Go to the **Chat** section (left sidebar)
2. Start a **new chat** or use an existing one
3. **IMPORTANT:** Before asking questions, select your Knowledge Base:
   - Look for a button/dropdown that says **"Attach Knowledge"**
   - It's usually near the top of the chat, above the message input field
   - Click it and **select your Knowledge Base** (e.g., "Company Docs")
4. Now type your question normally
5. The system will:
   - Convert your question to embeddings
   - Search ONLY in the selected Knowledge Base
   - Inject relevant document chunks as context
   - Return answers based on your documents
6. **View sources:** The response shows which documents were used for the answer

> **Important:** Without selecting a Knowledge Base, the chat will NOT include document context in its responses. Always select your Knowledge Base first!

