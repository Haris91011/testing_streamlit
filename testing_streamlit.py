import streamlit as st
import requests
import uuid
import os

# Configure the base URL for your FastAPI backend
BASE_URL = "https://testing.murshed.marahel.sa/"

def main():
    # Hard-coded parameters
    llm_model = "openai"
    embeddings_model = "openai"
    vectorstore_database = "qdrant"
    chunk_size = 1000
    chunk_overlap = 100

    # Title / Welcome message
    st.title("welcome To The Murshad")

    # Initialize session state variables if they don't exist
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "last_question" not in st.session_state:
        st.session_state.last_question = None
    if "chatbot_id" not in st.session_state:
        st.session_state.chatbot_id = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    # Track whether a PDF has been successfully processed
    if "document_processed" not in st.session_state:
        st.session_state.document_processed = False

    # ----- SIDEBAR -----
    with st.sidebar:
        st.header("Configuration")

        # Auto-generate chatbot_id and user_id if not present
        if not st.session_state.chatbot_id:
            st.session_state.chatbot_id = str(uuid.uuid4())
        if not st.session_state.user_id:
            st.session_state.user_id = str(uuid.uuid4())

        # Display the generated IDs
        st.info(f"Chatbot ID: {st.session_state.chatbot_id}")
        st.info(f"User ID: {st.session_state.user_id}")

        # Document Upload (only PDF)
        st.subheader("Document Upload (PDF only)")
        uploaded_files = st.file_uploader(
            "Upload PDF Documents",
            accept_multiple_files=True,  # Let them select multiple PDFs
            type=["pdf"]  # Accept only PDF files
        )

        # If files are uploaded, we check each file to ensure it's a PDF
        valid_pdf_files = []
        if uploaded_files:
            # Check extensions for each file
            for file in uploaded_files:
                # Extract file extension
                filename = file.name.lower()
                ext = os.path.splitext(filename)[1]

                if ext == ".pdf":
                    valid_pdf_files.append(file)
                else:
                    # Warn about non-PDF
                    st.warning(f"'{file.name}' is not a PDF. Please upload PDF files only.")

        # Process button for valid PDFs
        if st.button("Process Documents"):
            if not valid_pdf_files:
                st.warning("No valid PDF files to process. Please upload PDF files only.")
            else:
                with st.spinner("Processing documents..."):
                    try:
                        files = [
                            ('files', (file.name, file.read(), file.type))
                            for file in valid_pdf_files
                        ]

                        form_data = {
                            "chatbot_id": st.session_state.chatbot_id,
                            "chunk_size": str(chunk_size),
                            "chunk_overlap": str(chunk_overlap),
                            "embeddings_model": embeddings_model,
                            "vectorstore_name": vectorstore_database,
                            "llm": llm_model
                        }

                        response = requests.post(
                            f"{BASE_URL}/api/Ingestion_File",
                            files=files,
                            data=form_data
                        )

                        if response.status_code == 200:
                            st.success("PDF(s) processed successfully!")
                            st.session_state.document_processed = True
                        else:
                            st.error(
                                f"Error: {response.json().get('message', 'Unknown error occurred')}"
                            )
                    except Exception as e:
                        st.error(f"Error processing documents: {str(e)}")

    # ---- END SIDEBAR ----

    # Ensure we have a user ID and chatbot ID
    if not st.session_state.user_id or not st.session_state.chatbot_id:
        st.info("Chatbot ID and User ID not set. Please upload a PDF file to generate them automatically.")
        return

    # ---- CHAT INTERFACE ----
    chat_container = st.container()
    input_container = st.container()

    # If no document has been processed yet, show a prompt to the user
    if not st.session_state.document_processed:
        st.info("Please upload and process at least one PDF file to start chatting.")
        return

    # Otherwise, show the chat interface
    with input_container:
        st.markdown(
            "<div style='padding: 1rem; background-color: #f0f2f6; position: fixed; bottom: 0; "
            "right: 0; left: 0; z-index: 1000;'>",
            unsafe_allow_html=True
        )
        prompt = st.chat_input("Ask a question about your documents")
        st.markdown("</div>", unsafe_allow_html=True)

        if prompt:
            # Get AI response
            try:
                response = requests.post(
                    f"{BASE_URL}/api/chat-bot",
                    json={
                        "query": prompt,
                        "chatbot_id": st.session_state.chatbot_id,
                        "user_id": st.session_state.user_id
                    }
                )

                if response.status_code == 200:
                    ai_response = response.json()["data"]
                    st.session_state.chat_history.append(
                        {"role": "user", "content": prompt}
                    )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": ai_response}
                    )
                    st.session_state.last_question = prompt
                    st.session_state.last_response = ai_response
                    st.rerun()
                else:
                    st.error(
                        f"Error: {response.json().get('message', 'Unknown error occurred')}"
                    )
            except Exception as e:
                st.error(f"Error getting response: {str(e)}")

    # Display chat history
    with chat_container:
        st.markdown("<div style='margin-bottom: 100px'>", unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                # If backend returns dict with 'response' and 'source'
                if isinstance(message["content"], dict):
                    st.write(message["content"]["response"])
                    with st.expander("View Sources"):
                        for source in message["content"]["source"]:
                            st.write(f"Document: {source['documents']['filename']}")
                            st.write(
                                f"Pages: {', '.join(map(str, source['documents']['pages']))}"
                            )
                else:
                    st.write(message["content"])
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
