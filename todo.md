1. Add button to sidebar to change the response style: concise and to the point, normal, explanatory and unnecessarily pedantic 
2. Add button to disable/enable/force tool selection for each of the tools
# 3. Download button for RAG pdfs
4. Report html link when finding rag files in web_markdown folder
5. Show citations of weblinks used. 
# 6. Fix page scrolling
# 7. Add icon to export to markdown or word document
# 8. Add clear history button
# 9. Add persistent long-term memory and user management via cookies. 
10. Ensure that all different uploaded file formats are correct.
# 11. Add support for SPSS files
# 12. Add button to request for a different response 🔄
13. In the chat box allow to navigate to previous questions in the prompt using the up-down arrow keys
14. Add bm25 retriever to create hybrid search. Hybrid Search (similarity_search + BM25Retriever) e.g. https://github.com/chroma-core/chroma/issues/1686
15. Data view via itable
# 16. Use react agent from langgraph
17. Try to get the agent to extract data from the search results
# 18. Add button to download chat transcript and option to download specific response
19. Add verification of DOI links
20. Fix hallucinations of paper - use SS, RAG and wiki info

21. Initial suggested prompts seem to be always the same 
# 22. Add copy button after each chat message
# 23. Add upload data option
# 24.  Greeding message seems to always be the same
25. Fixed initial warning about cache
26. Add iframe support for dataframes
27. Ensure that code executaion works
28. Add more libraries about code execution (pymc, pystan, brms, rpy, etc)


add the ability to upload files in the sidebar. Acceptable files include SPSS files (.sav), Rdata, rds, csv, xlsx, pdf, docx, and md. If it is a document then the file should be read and user can ask questions about the content. The files should NOT be added to the RAG - but should be an alternative temporary resource for that user.  If it is a dataset it should be imported as a pandas data.frame and the user can ask questions about thier variables, what analysis to perform etc. They can also ask the ai to perform data analysis procedures. If the later the ai should use the code execution functionality to write python code and execute it to run the analysis                                      



Create a chatbot application using llamaindex and chainlit using gemini-2.5-flash for the LLM. For the app will read API keys from .env, and the system prompt from esi_agent_instruction.md. The app will be named "ESI: ESI Scholarly Instructor"

The ai agent will have access to different tools: tavily search, semantic scholar search, RAG using chromadb, scraping of websites and pdf files, and code execution. Depending on the query, question, interaction, or request from the user, the ai should decide which tool or tools to invoke.
The app should be organized in three files app.py (main app), ui.py (chainlit interface), and agent.py (the functionality of the agent and its tools)
For the rag you you create a separate script for ingesting documents. 
Users should be able to upload their own files and ask the ai questions about the files - but these should not be stored in the RAG. The files allowed include docx, md, pdf, xlsx, Rdata, csv, rds, sav (SPSS).
The app will have persistent memory/chats
Users should be able to change the LLM settings (primarily temperature).
The app will be named "ESI: ESI Scholarly Instructor"





-- `rag_search`: Search the internal knowledge base about the MSc dissertation module (NBS-7095x at UEA). Use this FIRST for questions about:                                    
-    - Module specifics: deadlines, procedures, milestones, handbook content, marking criteria.                                                                                  
-    - When you want to refer to the RAG in your responses, refer to it as your "knowledge base".                                                                                
-    - Do not recommend to the users to check your RAG or knowledge base as they do not have access. Only you have access to it and your role is to answer their questions.      
-    - UEA resources, staff members, ethical guidelines, forms.                                                                                                                  
-    - Reading lists, specific authors mentioned in module materials, previously discussed concepts/scales.                                                                      
-- `web_scraper`: Fetch the content of a specific webpage URL. Useful for getting details from a search result link.                                                             
-- `read_uploaded_document`: Reads the full text content of a document previously uploaded by the user. Input is the exact filename (e.g., 'my_dissertation.pdf'). Use this to   
answer questions about the content of uploaded documents.                                                                                                                        
-- `analyze_uploaded_dataframe`: Provides summary information (shape, columns, dtypes, head, describe) about a pandas DataFrame previously uploaded by the user. Input is the    
exact filename (e.g., 'my_data.csv'). Use this to understand the structure and basic statistics of uploaded datasets. For more complex analysis, use the 'code_interpreter' tool.
