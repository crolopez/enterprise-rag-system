# Data Indexing Guide

How to get your data into the Enterprise RAG system. There are two approaches with **important differences in how context is used**.

## Option 1: Web UI Upload (Manual) - Selective RAG

Upload documents through the web interface and **manually select which Knowledge Base to use** in each chat.

### How it works
1. Open http://localhost:3000
2. Upload documents to a named **Knowledge Base** (e.g., "Company Docs")
3. When chatting, **explicitly select** which Knowledge Base to use
4. LLM searches only in the selected Knowledge Base
5. You control exactly what context is available

### Context behavior
- Each chat must explicitly select a Knowledge Base
- Without selection, no document context is included
- Different chats can use different Knowledge Bases
- User must remember to select the right one

### Best for
- Testing, prototyping
- Sensitive data (organize by access level)
- Multiple document collections (keep them separate)
- Fine-grained context control

### Full details
[Web UI - Document Management](WEB_UI_DOCUMENTS.md)


## Option 2: Data Indexer Service (Automated) - Automatic RAG

Configure automatic indexing of files and external APIs. All indexed documents are **automatically searched** in every query.

### How it works
1. Define data sources in `config/data_sources.json`
2. Service automatically indexes on schedule
3. Documents stored in Qdrant collection (default: "documents")
4. **RAG Wrapper automatically searches all collections** on every query
5. Context is injected transparently - user doesn't select anything

### Context behavior
- Every question searches Qdrant automatically
- All indexed documents are considered for context
- No manual Knowledge Base selection needed
- Context is injected invisibly - like magic
- Consistent behavior across all queries

### Best for
- Production systems
- Continuous data synchronization (APIs, databases)
- "Always-on" context (want all docs searchable automatically)
- Custom data sources (with custom handlers)

### Full details
[Data Indexer Service](DATA_INDEXER.md)

## Quick Comparison

| Aspect | Web UI (Selective) | Data Indexer (Automatic) |
|--------|-------------------|--------------------------|
| **Setup** | None - just upload | Configure `data_sources.json` |
| **Frequency** | Manual | Scheduled/Continuous |
| **Data Sources** | Local file upload | Files, APIs, databases, custom |
| **Context Usage** | Must select Knowledge Base | Automatic on every query |
| **User Experience** | Explicit & controlled | Transparent & automatic |
| **Best Suited** | Testing, prototyping | Production, continuous sync |


## Which Should I Use?

- **Just experimenting?** → **Web UI** (no setup, you control what's included)
- **Want automatic RAG?** → **Data Indexer** (everything is searchable automatically)
- **Both approaches?** → **You can use them together** (documents from both will be available)
- **Production system?** → **Data Indexer** (automatic context, no user selection needed)
