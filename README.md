Here’s the **README.md** file code for your GitHub repository. This file provides a comprehensive overview of the project, installation instructions, usage guide, and details about experimental features like **CUDA support** and the **relevance checker agent**.

---

```markdown
# Hiring Assistant Chatbot

## Project Overview
The **Hiring Assistant Chatbot** is an AI-powered tool designed to streamline the technical hiring process. It assists recruiters and hiring managers by:
- Collecting candidate information securely.
- Generating role-specific technical questions.
- Evaluating candidate responses based on technical accuracy and role-specific requirements.
- Providing a detailed assessment report for internal review.

The chatbot is built using **Streamlit** for the user interface and **Ollama** for generating responses and evaluating answers. It ensures **GDPR compliance** by encrypting sensitive data and anonymizing candidate information.

---

## Installation Instructions

### Prerequisites
- Python 3.9.19 or higher
- Pip (Python package manager)

### Steps to Set Up and Run the Application
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/akshit7093/Hiring-chatbot.git
   cd Hiring-chatbot
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Ollama**:
   - Download and install Ollama from the [official website](https://ollama.ai/).
   - Start the Ollama server:
     ```bash
     ollama serve
     ```
   - Pull the required model:
     ```bash
     ollama pull llama3.1
     ```

5. **Run the Application**:
   ```bash
   streamlit run appp.py
   ```

6. **Access the Application**:
   - Open your browser and navigate to `http://localhost:8501`.

---

## Experimental Features

### 1. CUDA Support
The experimental version of the chatbot includes **CUDA support** for GPU acceleration. This feature is ideal for users with NVIDIA GPUs who want to leverage hardware acceleration for faster response generation and evaluation.

#### Steps to Enable CUDA Support
1. Ensure you have an NVIDIA GPU and the latest CUDA toolkit installed.
2. Install the required GPU-enabled libraries:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
3. Run the experimental version of the app:
   ```bash
   streamlit run appp_copy.py
   ```

### 2. Relevance Checker Agent
The experimental version includes a **relevance checker agent** powered by **Llama 2**. This agent evaluates whether a candidate's answer is relevant to the question before sending it to the main evaluation agent. This ensures that only relevant answers are evaluated, improving the accuracy of the feedback.

#### Steps to Use the Relevance Checker Agent
1. Ensure you have the experimental version of the app (`appp_copy.py`).
2. Run the app:
   ```bash
   streamlit run appp_copy.py
   ```
3. The relevance checker agent will automatically evaluate the relevance of each answer before proceeding with the main evaluation.

---

## Usage Guide

### 1. Collect Candidate Information
- Enter the candidate's details (e.g., name, email, phone, years of experience, desired position, tech stack).
- Click **Submit** to proceed.

### 2. Answer Technical Questions
- The chatbot will generate role-specific technical questions based on the candidate's tech stack.
- Answer each question and navigate between questions using the **Previous** and **Next** buttons.
- Click **Submit Answers** when done.

### 3. View Evaluation Results
- The chatbot will evaluate the candidate's answers and display a score along with technical feedback.
- Role-specific feedback is saved internally for hiring decisions.

### 4. Professional Discussion
- The chatbot can discuss the candidate's technical expertise, role requirements, and next steps in the hiring process.

---

## Technical Details

### Libraries Used
- **Streamlit**: For building the web-based user interface.
- **Ollama**: For generating responses and evaluating answers using AI models.
- **Cryptography**: For encrypting and decrypting sensitive candidate data.
- **CSV**: For saving candidate responses and evaluation results.
- **JSON**: For loading role-specific requirements.

### Model Details
- The chatbot uses the **Llama 3.1** model from Ollama for generating responses and evaluating answers.

### Architectural Decisions
- **Data Privacy**: Sensitive candidate data is encrypted and anonymized to ensure GDPR compliance.
- **Role-Specific Requirements**: Each role has a JSON file containing specific requirements, which are used to evaluate the candidate's suitability.
- **Modular Design**: The code is organized into functions for encryption, question generation, answer evaluation, and report generation.

---

## Prompt Design

### 1. Information Gathering
- The chatbot uses structured prompts to collect candidate information securely.
- Example:
  ```plaintext
  Please provide your full name, email, phone number, years of experience, desired position, and tech stack.
  ```

### 2. Technical Question Generation
- The chatbot generates technical questions based on the candidate's selected tech stack.
- Example:
  ```plaintext
  Generate exactly 4 technical interview questions for a candidate with experience in Python, Django, and AWS.
  ```

### 3. Answer Evaluation
- The chatbot evaluates candidate answers using strict technical standards.
- Example:
  ```plaintext
  Evaluate if the answer demonstrates clear understanding and technical accuracy. First line must be exactly "CORRECT" or "INCORRECT".
  ```

### 4. Role-Specific Evaluation
- The chatbot evaluates the candidate's suitability for the role based on predefined requirements.
- Example:
  ```plaintext
  Based on the candidate's answers, does the candidate meet the requirement: "Strong programming skills in Python"? First line must be exactly "YES" or "NO".
  ```

---

## Challenges & Solutions

### 1. Handling Sensitive Data
- **Challenge**: Ensuring GDPR compliance while collecting and storing sensitive candidate information.
- **Solution**: Implemented encryption and anonymization for sensitive data. Used the `cryptography` library to encrypt data before storage.

### 2. Generating Role-Specific Questions
- **Challenge**: Creating dynamic and relevant technical questions based on the candidate's tech stack.
- **Solution**: Used Ollama to generate questions in real-time based on the candidate's selected tech stack.

### 3. Evaluating Answers Accurately
- **Challenge**: Ensuring consistent and fair evaluation of candidate answers.
- **Solution**: Designed strict evaluation prompts and used Ollama to evaluate answers based on technical accuracy and depth.

### 4. Role-Specific Feedback
- **Challenge**: Evaluating candidate suitability for specific roles without sharing feedback directly with the user.
- **Solution**: Saved role-specific feedback to a CSV file for internal review and displayed only technical feedback to the user.

---

## Future Enhancements
- **Integration with ATS**: Integrate the chatbot with Applicant Tracking Systems (ATS) for seamless candidate management.
- **Multi-Language Support**: Add support for multiple programming languages and frameworks.
- **Advanced Analytics**: Provide detailed analytics and insights into candidate performance.

---

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeatureName`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeatureName`).
5. Open a pull request.

---

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact
For questions or feedback, please contact:
- **Your Name**: [akshitsharma7093@gmail.com](akshitsharma7093@gmail.com)
- **GitHub**: [akshit7093](https://github.com/7093)
```

