import os
import streamlit as st
import ollama
import json
import csv
from datetime import datetime, timedelta
from cryptography.fernet import Fernet


import torch  # Import PyTorch to check GPU availability

# Check if GPU is available
if torch.cuda.is_available():
    device = torch.device("cuda")
    st.sidebar.write("GPU is available and will be used for processing.")
else:
    device = torch.device("cpu")
    st.sidebar.write("GPU is not available. Using CPU instead.")

    
# Generate a key for encryption (store this securely in a key management system)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Function to encrypt data
def encrypt_data(data):
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data

# Function to decrypt data
def decrypt_data(encrypted_data):
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
    return decrypted_data

# Function to anonymize candidate data (for GDPR compliance)
def anonymize_candidate_data(candidate_data):
    anonymized_data = candidate_data.copy()
    anonymized_data["full_name"] = "ANONYMIZED"
    anonymized_data["email"] = "ANONYMIZED@example.com"
    anonymized_data["phone"] = "ANONYMIZED"
    return anonymized_data

# Function to delete candidate data after retention period (for GDPR compliance)
def delete_candidate_data_after_retention(file_path, retention_days=30):
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            # Get the file's last modification time
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # Check if the retention period has passed
            if datetime.now() - file_mod_time > timedelta(days=retention_days):
                os.remove(file_path)
                st.sidebar.write(f"Candidate data deleted after {retention_days} days retention period.")
            else:
                # Only log this message once per session
                if "retention_message_displayed" not in st.session_state:
                    st.sidebar.write(f"Retention period not yet reached. Data will be deleted after {retention_days} days.")
                    st.session_state.retention_message_displayed = True
        else:
            # Only log this message once per session
            if "no_data_message_displayed" not in st.session_state:
                st.sidebar.write("No candidate data found to delete.")
                st.session_state.no_data_message_displayed = True
    except Exception as e:
        st.sidebar.error(f"Error deleting candidate data: {str(e)}")

# Function to load role-specific requirements
def load_role_requirements(role):
    role_file = f"{role.lower().replace(' ', '_')}.json"
    if os.path.exists(role_file):
        with open(role_file, "r") as file:
            return json.load(file)
    else:
        st.error(f"Role requirements file for '{role}' not found.")
        return None

# Streamlit UI
st.title("TalentScout Hiring Assistant Chatbot")

# Initialize session state for conversation history and candidate information
if "messages" not in st.session_state:
    st.session_state.messages = []
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {
        "full_name": None,
        "email": None,
        "phone": None,
        "years_of_experience": None,
        "desired_position": None,
        "current_location": None,
        "tech_stack": None,
    }
if "info_collected" not in st.session_state:
    st.session_state.info_collected = False
if "technical_questions" not in st.session_state:
    st.session_state.technical_questions = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "conversation_ended" not in st.session_state:
    st.session_state.conversation_ended = False

# Function to detect sensitive queries
def handle_sensitive_query(user_message):
    sensitive_keywords = ["name", "email", "phone", "contact", "details"]
    user_message_lower = user_message.lower()
    
    # Check if the user is asking about sensitive information
    for keyword in sensitive_keywords:
        if keyword in user_message_lower:
            return True
    return False

def generate_response(prompt):
    """
    Generate a response using Ollama with GPU acceleration.
    """
    if handle_sensitive_query(prompt):
        return "For privacy reasons, I cannot display your personal details directly. However, I can confirm that your information is securely stored and will only be used for the hiring process. Let me know if you have any other questions about the interview process or your technical skills!"
    
    try:
        # Ensure Ollama uses the GPU if available
        response = ollama.generate(
            model="llama3.1",  # Use 'llama3.1' or any other GPU-accelerated model
            prompt=prompt,
        )
        return response["response"]
    except Exception as e:
        return f"Error generating response: {str(e)}"

def generate_technical_questions(tech_stack):
    """
    Generate technical questions using Ollama with GPU acceleration.
    """
    if not tech_stack:
        return []

    prompt = f"""
    Generate exactly 4 technical interview questions for a candidate with experience in: {', '.join(tech_stack)}

    Return only a JSON array in this exact format:
    [
        {{"question": "Your first question here", "type": "text"}},
        {{"question": "Your second question here", "type": "code"}},
        {{"question": "Your third question here", "type": "text"}},
        {{"question": "Your fourth question here", "type": "code"}}
    ]
    """
    
    try:
        # Ensure Ollama uses the GPU if available
        response = ollama.generate(
            model="llama3.1",  # Use 'llama3.1' or any other GPU-accelerated model
            prompt=prompt,
        )
        response_text = response["response"].strip()
        
        # Extract the JSON array from the response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            questions = json.loads(json_str)
            
            # Validate question format
            if len(questions) >= 3 and all(isinstance(q, dict) and 'question' in q and 'type' in q for q in questions):
                return questions
                
        raise ValueError("Invalid question format received")
        
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return []


def is_answer_relevant(question, answer):
    """
    Use Llama 2 to check if the answer is relevant to the question.
    Returns:
        - True if the answer is relevant.
        - False if the answer is irrelevant.
    """
    # Construct relevance check prompt
    prompt = f"""
    You are a technical interviewer evaluating whether a candidate's answer is relevant to the question.

    Question: {question}
    Candidate's Answer: {answer}

    Instructions:
    1. Evaluate whether the answer is relevant to the question.
    2. Focus on technical accuracy and alignment with the question's requirements.
    3. Your response must be exactly "RELEVANT" or "NOT RELEVANT".
    4. Do not include any additional text or explanations.

    Evaluation:
    """

    try:
        # Generate evaluation using Llama 2
        response = ollama.generate(model="llama3.1", prompt=prompt)
        evaluation_text = response["response"].strip().upper()

        # Parse the evaluation result
        if evaluation_text == "RELEVANT":
            return True
        elif evaluation_text == "NOT RELEVANT":
            return False
        else:
            # Attempt to infer relevance from the response
            if "relevant" in evaluation_text.lower():
                return True
            elif "not relevant" in evaluation_text.lower():
                return False
            else:
                raise ValueError("Invalid evaluation format")
    except Exception as e:
        # Handle errors gracefully
        st.error(f"Error checking relevance: {str(e)}")
        return False  # Assume irrelevant if there's an error


def evaluate_answers(questions, answers, role_requirements):
    """
    Evaluate candidate answers and provide consistent feedback.
    Returns:
        - score: Total score based on technical questions.
        - feedback: Feedback for each technical question.
        - role_feedback: Feedback on how well the candidate meets role-specific requirements.
    """
    score = 0
    feedback = []
    role_feedback = []

    # Evaluate technical questions
    for i, question in enumerate(questions):
        candidate_answer = answers[i].strip()  # Remove leading/trailing whitespace

        # Check if the answer is empty
        if not candidate_answer:
            feedback.append(f"Question {i + 1}: Incorrect (0 points) - No answer provided.")
            continue

        # Check if the answer is relevant using the relevance checker agent
        if not is_answer_relevant(question["question"], candidate_answer):
            feedback.append(f"Question {i + 1}: Incorrect (0 points) - Answer is irrelevant to the question.")
            continue

        # Construct evaluation prompt for technical questions
        prompt = f"""
        You are a technical interviewer. Evaluate this answer with high standards.

        Question: {question["question"]}
        Candidate's Answer: {candidate_answer}

        Instructions:
        1. First line must be exactly "CORRECT" or "INCORRECT".
        2. Provide a brief explanation of why the answer is correct or incorrect.
        3. Keep the explanation concise and focused on technical accuracy.
        4. If you cannot evaluate the answer, start your response with "ERROR".

        Evaluation:
        """

        try:
            # Generate evaluation using Llama 2
            response = ollama.generate(model="llama3.1", prompt=prompt)
            evaluation_text = response["response"].strip()

            # Parse the evaluation result
            evaluation_lines = evaluation_text.split('\n')
            if len(evaluation_lines) == 0:
                raise ValueError("Empty evaluation response")

            # Extract the first line (CORRECT/INCORRECT/ERROR)
            evaluation = evaluation_lines[0].strip().upper()

            # Handle invalid evaluation format
            if evaluation not in ["CORRECT", "INCORRECT", "ERROR"]:
                # Attempt to infer evaluation from the response
                if "correct" in evaluation_text.lower():
                    evaluation = "CORRECT"
                elif "incorrect" in evaluation_text.lower():
                    evaluation = "INCORRECT"
                else:
                    raise ValueError("Invalid evaluation format")

            # Extract the explanation
            explanation = ' '.join(evaluation_lines[1:]).strip() if len(evaluation_lines) > 1 else "No explanation provided."

            # Update score and feedback based on evaluation
            if evaluation == "CORRECT":
                score += 1 if question["type"] == "text" else 2
                feedback.append(f"Question {i + 1}: Correct ({1 if question['type'] == 'text' else 2} points) - {explanation}")
            elif evaluation == "INCORRECT":
                feedback.append(f"Question {i + 1}: Incorrect (0 points) - {explanation}")
            else:
                feedback.append(f"Question {i + 1}: Evaluation failed (0 points) - Error: Unable to evaluate the answer.")

        except Exception as e:
            # Handle errors gracefully
            feedback.append(f"Question {i + 1}: Evaluation failed (0 points) - Error: {str(e)}")

    # Evaluate role-specific requirements
    if role_requirements and "requirements" in role_requirements:
        for requirement in role_requirements["requirements"]:
            # Construct evaluation prompt for role-specific requirements
            prompt = f"""
            You are a technical interviewer evaluating a candidate's suitability for the role of {role_requirements["role"]}.

            Requirement: {requirement}

            Based on the candidate's answers, does the candidate meet this requirement?
            Instructions:
            1. First line must be exactly "YES" or "NO".
            2. Provide a brief explanation of why the candidate meets or does not meet the requirement.
            3. Keep the explanation concise and focused on role alignment.
            4. If you cannot evaluate the requirement, start your response with "ERROR".

            Evaluation:
            """

            try:
                # Generate evaluation using Llama 2
                response = ollama.generate(model="llama3.1", prompt=prompt)
                evaluation_text = response["response"].strip()

                # Parse the evaluation result
                evaluation_lines = evaluation_text.split('\n')
                if len(evaluation_lines) == 0:
                    raise ValueError("Empty evaluation response")

                # Extract the first line (YES/NO/ERROR)
                evaluation = evaluation_lines[0].strip().upper()

                # Handle invalid evaluation format
                if evaluation not in ["YES", "NO", "ERROR"]:
                    # Attempt to infer evaluation from the response
                    if "yes" in evaluation_text.lower():
                        evaluation = "YES"
                    elif "no" in evaluation_text.lower():
                        evaluation = "NO"
                    else:
                        raise ValueError("Invalid evaluation format")

                # Extract the explanation
                explanation = ' '.join(evaluation_lines[1:]).strip() if len(evaluation_lines) > 1 else "No explanation provided."

                # Add role-specific feedback
                if evaluation == "YES":
                    role_feedback.append(f"Requirement: {requirement} - Met (1 point) - {explanation}")
                elif evaluation == "NO":
                    role_feedback.append(f"Requirement: {requirement} - Not Met (0 points) - {explanation}")
                else:
                    role_feedback.append(f"Requirement: {requirement} - Evaluation failed (0 points) - Error: Unable to evaluate the requirement.")

            except Exception as e:
                # Handle errors gracefully
                role_feedback.append(f"Requirement: {requirement} - Evaluation failed (0 points) - Error: {str(e)}")

    return score, feedback, role_feedback


def is_gibberish(text):
    """
    Check if the text is gibberish or irrelevant.
    """
    # Define a list of irrelevant or gibberish patterns
    irrelevant_patterns = ["wadawd", "asdf", "1234", "test", "placeholder", "lorem ipsum", "dawdawdaw"]

    # Check if the text is too short or matches irrelevant patterns
    if len(text) < 5 or any(pattern in text.lower() for pattern in irrelevant_patterns):
        return True
    return False

def save_to_csv(candidate_info, questions, answers, score, feedback, role_feedback):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = "secure_interview_responses.csv"
    
    # Anonymize candidate data
    anonymized_data = anonymize_candidate_data(candidate_info)
    
    # Prepare the data row
    row_data = {
        'Timestamp': timestamp,
        'Full Name': anonymized_data['full_name'],
        'Email': anonymized_data['email'],
        'Phone': anonymized_data['phone'],
        'Years of Experience': anonymized_data['years_of_experience'],
        'Desired Position': anonymized_data['desired_position'],
        'Current Location': anonymized_data['current_location'],
        'Tech Stack': ', '.join(anonymized_data['tech_stack']),
        'Total Score': score
    }
    
    # Add questions and answers
    for i, (question, answer) in enumerate(zip(questions, answers)):
        row_data[f'Question_{i+1}'] = question['question']
        row_data[f'Answer_{i+1}'] = answer
        row_data[f'Feedback_{i+1}'] = feedback[i]
    
    # Add role-specific feedback (for internal use only)
    for i, fb in enumerate(role_feedback):
        row_data[f'Role_Feedback_{i+1}'] = fb
    
    # Check if file exists to write headers
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(row_data.keys()))
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row_data)

# Display a short greeting message at the beginning
if "greeting_displayed" not in st.session_state:
    st.write("Hi! I'm the Hiring Assistant from TalentScout. Let's get started by filling out some details.")
    st.session_state.greeting_displayed = True

# Step 1: Collect candidate information
if not st.session_state.info_collected and not st.session_state.conversation_ended:
    with st.form("candidate_details_form"):
        st.write("### Step 1: Provide Your Details")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        phone = st.text_input("Phone Number")
        years_of_experience = st.number_input("Years of Experience", min_value=0, max_value=50, step=1)
        
        # Role selection dropdown
        roles = ["Software Engineer", "Data Scientist", "Machine Learning Engineer", "DevOps Engineer"]
        desired_position = st.selectbox("Desired Position", roles)
        
        current_location = st.text_input("Current Location")
        tech_stack = st.multiselect(
            "Tech Stack (Select all that apply)",
            ["Python", "Java", "JavaScript", "Django", "React", "PostgreSQL", "AWS", "Machine Learning"]
        )
        submitted = st.form_submit_button("Submit")

        if submitted:
            # Save candidate information to session state (encrypted)
            st.session_state.candidate_info = {
                "full_name": encrypt_data(full_name),
                "email": encrypt_data(email),
                "phone": encrypt_data(phone),
                "years_of_experience": years_of_experience,
                "desired_position": desired_position,
                "current_location": current_location,
                "tech_stack": tech_stack,
            }
            st.session_state.info_collected = True
            
            # Load role-specific requirements
            role_requirements = load_role_requirements(desired_position)
            if role_requirements:
                st.session_state.role_requirements = role_requirements
                st.session_state.technical_questions = generate_technical_questions(tech_stack)
                if not st.session_state.technical_questions:
                    st.error("Failed to generate technical questions. Please try again.")
                    st.session_state.info_collected = False
                else:
                    st.session_state.answers = [""] * len(st.session_state.technical_questions)
                    st.rerun()
            else:
                st.session_state.info_collected = False

# Step 2: Question-Answer Session
if st.session_state.info_collected and not st.session_state.submitted and not st.session_state.conversation_ended:
    if not st.session_state.technical_questions:
        st.error("No technical questions were generated. Please restart the session.")
    else:
        st.write("### Step 2: Answer the Questions")
        current_question = st.session_state.technical_questions[st.session_state.current_question_index]
        st.write(f"#### Question {st.session_state.current_question_index + 1}")
        st.write(current_question["question"])

        # Input field for the answer
        answer_key = f"answer_{st.session_state.current_question_index}"  # Unique key for each question
        if current_question["type"] == "text":
            answer = st.text_area("Your Answer", value=st.session_state.answers[st.session_state.current_question_index], key=answer_key)
        elif current_question["type"] == "code":
            answer = st.text_area("Write your code here", value=st.session_state.answers[st.session_state.current_question_index], key=answer_key)

        # Save the answer to session state
        if answer:
            st.session_state.answers[st.session_state.current_question_index] = answer

        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.current_question_index > 0:
                if st.button("Previous"):
                    st.session_state.current_question_index -= 1
                    st.rerun()
        with col2:
            if st.session_state.current_question_index < len(st.session_state.technical_questions) - 1:
                if st.button("Next"):
                    st.session_state.current_question_index += 1
                    st.rerun()
            else:
                if st.button("Submit Answers"):
                    # Ensure the last answer is saved before submission
                    if answer:
                        st.session_state.answers[st.session_state.current_question_index] = answer
                    st.session_state.submitted = True
                    st.rerun()

# Step 3: Evaluate Answers
if st.session_state.submitted and not st.session_state.conversation_ended:
    st.write("### Evaluation Results")
    score, feedback, role_feedback = evaluate_answers(
        st.session_state.technical_questions,
        st.session_state.answers,
        st.session_state.role_requirements
    )
    st.write(f"#### Your Score: {score}/{len(st.session_state.technical_questions) * 2}")

    st.write("#### Technical Feedback:")
    for fb in feedback:
        st.write(fb)
        
    # Save responses to CSV securely (including role-specific feedback for internal use)
    save_to_csv(
        st.session_state.candidate_info,
        st.session_state.technical_questions,
        st.session_state.answers,
        score,
        feedback,
        role_feedback  # Role-specific feedback is saved but not displayed
    )

    # Provide next steps
    st.write("### Next Steps")
    st.write("We will review your responses and get back to you shortly.")

    # Option to restart or end the session
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Restart"):
            st.session_state.info_collected = False
            st.session_state.technical_questions = []
            st.session_state.answers = []
            st.session_state.submitted = False
            st.session_state.current_question_index = 0
            st.rerun()
    with col2:
        if st.button("End Session"):
            st.session_state.conversation_ended = True
            st.write("Thank you for participating! Have a great day!")

def generate_candidate_report(candidate_info, questions, answers, score, chat_history, role_requirements):
    total_possible_score = len(questions) * 2
    score_percentage = (score / total_possible_score) * 100

    # Calculate ratings for each evaluation criterion
    technical_proficiency = (score / total_possible_score) * 10  # Scale to 10
    answer_quality = (score / total_possible_score) * 10  # Scale to 10
    role_fit = (score / total_possible_score) * 10  # Scale to 10

    # Determine recommendation
    recommendation = "HIRE" if score_percentage >= 70 else "NO HIRE"
    reason = (
    "their strong technical proficiency and alignment with role requirements."
    if recommendation == "HIRE"
    else "gaps in technical proficiency or role alignment."
)

    # Generate strengths and areas for improvement
    strengths = [
        "Strong coding skills in Python.",
        "Good understanding of database operations.",
    ]
    areas_for_improvement = [
        "Needs to improve theoretical knowledge of frameworks like Django.",
        "Should practice explaining complex concepts in detail.",
    ]

    # Generate summaries for evaluation criteria
    technical_summary = (
        "strong technical skills and a solid understanding of core concepts."
        if technical_proficiency >= 7
        else "some gaps in technical knowledge that need improvement."
    )
    answer_summary = (
        "clear, accurate, and well-structured responses."
        if answer_quality >= 7
        else "some inaccuracies or lack of depth in responses."
    )
    role_summary = (
        "a good fit for the role based on their technical skills and experience."
        if role_fit >= 7
        else "not fully aligned with the role requirements."
    )

    # Generate the report
    report = f"""
### Technical Assessment Report

#### Candidate Information:
- **Name**: {anonymize_candidate_data(candidate_info)['full_name']}
- **Role**: {candidate_info['desired_position']}
- **Experience**: {candidate_info['years_of_experience']} years
- **Tech Stack**: {', '.join(candidate_info['tech_stack'])}
- **Score**: {score}/{total_possible_score} ({score_percentage:.1f}%)

---

#### Evaluation Summary:
- **Technical Proficiency**: {technical_proficiency:.1f}/10 - The candidate demonstrates {technical_summary}
- **Answer Quality**: {answer_quality:.1f}/10 - The candidate's answers were {answer_summary}
- **Role Fit**: {role_fit:.1f}/10 - The candidate is {role_summary}
- **Recommendation**: {recommendation}

---

#### Detailed Evaluation:

##### 1. Technical Proficiency:
- **Rating**: {technical_proficiency:.1f}/10
- **Summary**: The candidate has {technical_summary}

##### 2. Answer Quality:
- **Rating**: {answer_quality:.1f}/10
- **Summary**: The candidate provided {answer_summary}

##### 3. Role Fit:
- **Rating**: {role_fit:.1f}/10
- **Summary**: The candidate is {role_summary}

---

#### Key Strengths:
- {strengths[0]}
- {strengths[1]}

#### Areas for Improvement:
- {areas_for_improvement[0]}
- {areas_for_improvement[1]}

---

#### Recommendations:
- Engage in structured learning experiences (e.g., online courses, tutorials) to improve technical skills.
- Practice responding to technical questions and scenarios.
- Seek guidance from experienced professionals on software engineering principles and best practices.

---

#### Conclusion:
Based on the assessment, the candidate is recommended for **{recommendation}** due to {reason}. They should focus on the following areas to enhance their technical proficiency and role fit:
- {areas_for_improvement[0]}
- {areas_for_improvement[1]}
    """
    return report

if st.session_state.submitted and not st.session_state.conversation_ended:
    st.write("### Step 4: Professional Discussion")
    st.markdown("""
    Let's discuss your technical expertise and career fit at TalentScout. You can:
    - 🎯 Get feedback on your technical assessment
    - 💼 Learn about role requirements and expectations
    - 📈 Explore growth opportunities in your tech stack
    - 🔍 Understand next steps in the hiring process
    """)

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    user_message = st.chat_input("Discuss your technical career path...")
    
    if user_message:
        with st.chat_message("user"):
            st.write(user_message)
        
        # Enhanced context-aware prompt
        chat_prompt = f"""
        You are TalentScout's Technical Hiring Assistant. Focus on:
        
        Context:
        - Role: {st.session_state.candidate_info['desired_position']}
        - Technologies: {', '.join(st.session_state.candidate_info['tech_stack'])}
        - Technical Assessment Score: {score}/{len(st.session_state.technical_questions) * 2}
        - Experience Level: {st.session_state.candidate_info['years_of_experience']} years

        Current Question: {user_message}

        Provide responses that:
        1. Stay focused on technical recruitment and assessment
        2. Give specific feedback on technical skills
        3. Explain role-specific requirements
        4. Suggest concrete improvement paths in their tech stack
        5. Maintain professional recruitment context
        6. Include next steps in the hiring process when relevant

        Keep responses concise, technical, and recruitment-focused.
        """
        
        response = generate_response(chat_prompt)
        
        with st.chat_message("assistant"):
            st.write(response)
        
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Professional exit options
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Complete Interview Process"):
            st.session_state.conversation_ended = True
            
            # Generate and display report
            st.write("### Technical Assessment Report")
            report = generate_candidate_report(
                st.session_state.candidate_info,
                st.session_state.technical_questions,
                st.session_state.answers,
                score,
                st.session_state.chat_history,
                st.session_state.role_requirements
            )
            
            # Display report in a structured format
            st.markdown(report)
            
            # Save report to CSV along with other data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_data = {
                'Timestamp': timestamp,
                'Candidate_Name': anonymize_candidate_data(st.session_state.candidate_info)['full_name'],
                'Position': st.session_state.candidate_info['desired_position'],
                'Experience': st.session_state.candidate_info['years_of_experience'],
                'Tech_Stack': ', '.join(st.session_state.candidate_info['tech_stack']),
                'Score': score,
                'Technical_Report': report
            }
            
            # Save to CSV
            report_filename = "technical_assessment_reports.csv"
            report_exists = os.path.isfile(report_filename)
            
            with open(report_filename, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=list(report_data.keys()))
                if not report_exists:
                    writer.writeheader()
                writer.writerow(report_data)
            
            st.write("---")
            st.write("Thank you for completing the technical screening process. Our recruitment team will review your profile and contact you soon.")
    with col2:
        if st.button("Start New Application"):
            st.session_state.clear()
            st.rerun()

def fallback_response():
    """
    Provides a meaningful response when the chatbot does not understand the input.
    """
    return "I'm sorry, I didn't understand that. Could you please rephrase or ask something else?"

# Fallback mechanism for unexpected inputs
if st.session_state.info_collected and not st.session_state.conversation_ended:
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_user_message = st.session_state.messages[-1]["content"]
        if "unable to generate" in st.session_state.messages[-1]["content"].lower():
            bot_response = fallback_response()
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            with st.chat_message("assistant"):
                st.markdown(bot_response)

# Display collected candidate information (for debugging purposes)
st.sidebar.title("Collected Candidate Information")
st.sidebar.json(st.session_state.candidate_info)

# Delete candidate data after retention period
delete_candidate_data_after_retention("secure_interview_responses.csv", retention_days=30)