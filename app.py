import streamlit as st
import zipfile
import os
import tempfile
from dotenv import load_dotenv
import shutil
import os
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import utils
from reportlab.pdfbase import pdfmetrics

# Load OpenAI API key from .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("OpenAI API key is not set. Please set it in your environment or .env file.")
else:
    client = OpenAI(api_key=api_key)

# Set page title
st.title("Java 8 to Java 17")
st.subheader("Code Assessment Tool")

# CSS to wrap text in code blocks
st.markdown("""
    <style>
    .streamlit-expander-content pre, .element-container pre {
        white-space: pre-wrap;        /* Wrap long lines */
        word-break: break-word;       /* Break long words if needed */
    }
    </style>
""", unsafe_allow_html=True)

# File upload
uploaded_file = st.file_uploader("Upload a ZIP file containing your Java 8 project.", type="zip")

improvements = []
report_filename= ""

# Define a function to wrap text within page width
def wrap_text(text, width, font_name, font_size):
    words = text.split()
    lines = []
    current_line = []
    current_width = 0
    space_width = pdfmetrics.stringWidth(" ", font_name, font_size)
    
    for word in words:
        word_width = pdfmetrics.stringWidth(word, font_name, font_size)
        if current_width + word_width + space_width > width:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_width = word_width
        else:
            current_line.append(word)
            current_width += word_width + space_width

    if current_line:
        lines.append(" ".join(current_line))

    return lines

if uploaded_file:
    # Create a temporary directory to extract the ZIP contents
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)

        # Scan the directory for Java files
        java_files = []
        extensions = (".java", ".xml", ".sh", ".bat", ".yml", ".properties", ".md", ".MF")
        for root, _, files in os.walk(tmpdirname):
            for file in files:
                if file.endswith(extensions):
                    java_files.append(os.path.join(root, file))

        if java_files:
            st.write("Java project files found:")
            st.write([os.path.relpath(file, tmpdirname) for file in java_files])

            # Analyze each Java file and get recommendations
            improvements = []
            for file_path in java_files:
                with open(file_path, 'r') as file:
                    code_content = file.read()
                    
                # Create the prompt
                prompt = """
                Assume the role of a senior Java developer or a Java Architect at Google, highly skilled in Java 17, with extensive experience in upgrading and modernizing legacy Java code. Analyze the provided Java 8 code and recommend targeted improvements to ensure full compatibility with Java 17. Your suggestions should focus on language feature upgrades, API replacements, modularization, and any necessary adjustments for deprecated or removed features. Aim to transform the code to not only function correctly but also adhere to Java 17 best practices, prioritizing readability and maintainability.

                Focus on:
                
                1. Replace any deprecated methods or classes with recommended alternatives.
                
                2. New Language Features: Integrate relevant language features from Java 9 through Java 17, such as `var`, `text blocks`, or `sealed classes`, to enhance readability, performance, or functionality.
                
                3. Modularization: If applicable, outline any potential for modularization with the Java Platform Module System introduced in Java 9.
                
                4. Performance Enhancements: Suggest optimizations that leverage improvements made in newer Java versions.
                Enhanced APIs and Libraries: Recommend the use of any improved or new APIs introduced in later Java versions, such as java.time enhancements, java.util.concurrent improvements, and new collections factory methods (List.of, Map.of, etc.) for concise and immutable collections creation.

                5. Pattern Matching and Type Checking: If the code involves complex instanceof checks or casting, leverage Java 16’s pattern matching for instanceof and Java 17's sealed types to simplify type-checking and improve code readability.

                6. Stream API and Optional Improvements: Review and enhance the use of the Stream API with new methods like Stream.toList(), and suggest improvements in handling optional values, as Java 9 onward introduced new methods in Optional (like ifPresentOrElse) that can simplify the code.

                7. Switch Expressions: If there are multiple switch statements, suggest using switch expressions introduced in Java 12 and enhanced in Java 14 to reduce verbosity, especially when handling multiple cases or returning values directly.

                8. Record Classes: If the code contains simple data-holding classes, suggest replacing these with record classes introduced in Java 14. This can improve clarity and reduce boilerplate for immutable data structures.

                9. Security and Encryption Updates: Java 9+ offers improved security features and encryption APIs. If relevant, recommend any updated security practices or classes to replace outdated or insecure methods.

                10. Garbage Collection Tuning and JVM Optimizations: For performance-sensitive applications, provide recommendations on using new garbage collection options (e.g., ZGC or Shenandoah) or JVM flags introduced in Java 9-17, focusing on optimizing memory management.

                11. Enhanced Null Safety and Annotations: Suggest improvements using annotations for null safety and the optional @Override, @Deprecated in applicable places to clarify intent, especially helpful with IDE-based inspections.

                12. Native Memory Access (Project Panama): If the code involves substantial native calls or Unsafe API usage, consider suggesting the experimental foreign-memory access APIs as a safer alternative introduced in later Java versions.

                13. Identify and Address Breaking Changes: Outline specific breaking changes introduced in each Java version between 9 and 17, such as changes in access modifiers, reflection limitations, or package-level restrictions. Highlight any code areas relying on setAccessible or reflective access to JDK-internal APIs, which are no longer allowed by default due to stronger encapsulation in the Java Platform Module System.

                14. Removed and Deprecated APIs: Identify APIs marked for removal since Java 8 and those actually removed in later versions. Replace these with the recommended alternatives. For instance:

                15. JDK-Internals and Sun Packages: Remove dependencies on sun.* or com.sun.* packages. Many of these have been restricted or removed, and alternatives are required (e.g., sun.misc.BASE64Encoder replaced with java.util.Base64).
                Deprecated XML and CORBA APIs: Java 9 removed the javax.xml.ws, javax.jws, and CORBA modules. Suggest replacements for any SOAP, CORBA, or JAX-WS API usages.
                
                16. JEP Removals and Deprecations: Monitor for JEPs related to API removals, such as JEP 277 (Enhanced Deprecation) and JEP 320 (Remove the Java EE and CORBA Modules), and propose migration strategies.
                Java EE Modules Removal: Since Java 11, Java EE modules like java.xml.ws, java.xml.bind, and java.activation have been removed. If the codebase depends on Java EE modules, suggest migrating to standalone libraries (e.g., Jakarta EE or other maintained equivalents).

                17. Encapsulated JDK Internal APIs: With the introduction of strong encapsulation, internal APIs are no longer accessible by default. If the code uses internal APIs (e.g., sun.misc.Unsafe or sun.reflect.Reflection), replace these with standard APIs or recommend alternative libraries that achieve the same functionality.

                18. Java Serialization Security Changes: Java versions after 8 introduced serialization filtering to improve security. If the code uses Java serialization, suggest implementing serialization filters or moving to safer serialization frameworks (e.g., Kryo or JSON-based serialization) where appropriate.

                19. JavaFX Module Changes: If the code relies on JavaFX, note that JavaFX is no longer included in the JDK as of Java 11. Recommend using a separate dependency for JavaFX, like OpenJFX, and ensure the build process reflects this change.

                20. Tooling Changes (javac, jar, jlink): With the JDK evolving, certain tooling behavior has changed (e.g., javac, jar command updates, and the jlink tool for creating modular runtime images). Ensure that any build scripts or tool dependencies are updated to accommodate new syntax, flags, or modular features.

                21. Classpath vs. Module Path Conflicts: When transitioning to modules, code that depends on the traditional classpath might experience conflicts. Recommend restructuring the project for the module path, especially if the code relies on split packages or JARs that may cause compatibility issues on the module path.

                22. Multi-Release JAR Files: Suggest the use of multi-release JAR files, introduced in Java 9, if the project must support multiple Java versions concurrently. This technique can help retain compatibility across versions where certain APIs differ.
                
                23. Use internet to check for latest version of libraries such as https://mvnrepository.com/ and (https://mvnrepository.com/)

                **Output Requirements**:
                - Provide concise code snippets for each suggested improvement, focusing only on modified sections of the code, do not have to list the whole class code
                - Use a "before and after" format for each snippet.
                - Include brief explanations with each change, ensuring they are clear for a junior developer to understand, especially the rationale behind the change.
                - While being concise and without commentary, omitting preambles - without any introductory or conclusion text
                
                Review the following Java 8 code and provide your improvement suggestions:

                \n\n""" + code_content
    

                 # Send the prompt to OpenAI for improvement suggestions
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                # Only include this if you need an image or URL, otherwise remove
                                # {
                                #     "type": "image_url",
                                #     "image_url": {"url": "https://example.com/image.jpg"},
                                # },
                            ],
                        }
                    ],
                )

                # Extract response content
                suggestions = response.choices[0].message.content
                improvements.append((os.path.relpath(file_path, tmpdirname), suggestions))
                
            # PDF generation and download button
            if improvements:
                pdf_filename = "java_upgrade_report.pdf"
                
                # Use a temporary file for the PDF to avoid direct file handling in the main directory
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
                    pdf_filename = temp_pdf_file.name
                    # Generate PDF
                    width, height = letter
                    max_text_width = width - 60  # Margin for text within page boundaries
                    c = canvas.Canvas(pdf_filename, pagesize=letter)
                    font_size = 10
                    font_name = "Helvetica"
                    c.setFont(font_name, 10)
                    y = height - 40  # Starting point for text

                    for file, suggestion in improvements:
                        c.drawString(30, y, f"### {file}")
                        y -= 20
                        for line in suggestion.split('\n'):
                            wrapped_lines = wrap_text(line, max_text_width, font_name, font_size)
                            for wrapped_line in wrapped_lines:
                                c.drawString(30, y, wrapped_line)
                                y -= 15
                                if y < 40:  # New page if content exceeds page height
                                    c.showPage()
                                    c.setFont("Helvetica", font_size)
                                    y = height - 40

                    c.save()

                # Display PDF download button
                with open(pdf_filename, 'rb') as pdf_file:
                    st.download_button(
                        label="Download Assessment Report",
                        data=pdf_file.read(),
                        file_name="java_upgrade_assessment_report.pdf",
                        mime="application/pdf"
                    )
                
                # Cleanup the generated PDF
                os.remove(pdf_filename)


            # Display the results
            st.write("### Code Improvement Suggestions")
            for file, suggestion in improvements:
                st.write(f"##### {file}")
                st.code(suggestion, language="java")
                st.write("---")  # Adds a horizontal line divider
                
                # with st.expander(f"🔍 {file}"):
                    # st.write("### Suggested Improvement")
                    # st.code(suggestion)
                    

        else:
            st.error("No Java files found in the uploaded ZIP file.")



