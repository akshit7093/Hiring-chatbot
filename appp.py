import os
import streamlit as st
import ollama
import json
import csv
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

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

# Function to generate responses using Ollama
def generate_response(prompt):
    if handle_sensitive_query(prompt):
        return "For privacy reasons, I cannot display your personal details directly. However, I can confirm that your information is securely stored and will only be used for the hiring process. Let me know if you have any other questions about the interview process or your technical skills!"
    
    try:
        response = ollama.generate(
            model="llama3.1",  # You can use other models like "llama3" or "mistral"
            prompt=prompt,
        )
        return response["response"]
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Function to generate technical questions
def generate_technical_questions(tech_stack):
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
        response = ollama.generate(
            model="llama3.1",
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

def evaluate_answers(questions, answers, role_requirements):
    score = 0
    feedback = []

    # Evaluate technical questions
    for i, question in enumerate(questions):
        if question["type"] == "text":
            prompt = f"""
            You are a strict technical interviewer. Evaluate this answer with high standards.
            
            Question: {question["question"]}
            Candidate's Answer: {answers[i]}
            
            Evaluate if the answer demonstrates clear understanding and technical accuracy.
            First line must be exactly "CORRECT" or "INCORRECT"
            Then provide a brief explanation of why.
            """
            try:
                response = ollama.generate(
                    model="llama3.1",
                    prompt=prompt,
                )
                evaluation = response["response"].strip().split('\n')[0].upper()
                explanation = ' '.join(response["response"].strip().split('\n')[1:])
                
                if evaluation == "CORRECT":
                    score += 1
                    feedback.append(f"Question {i + 1}: Correct (1 point) - {explanation}")
                else:
                    feedback.append(f"Question {i + 1}: Incorrect (0 points) - {explanation}")
            except Exception as e:
                feedback.append(f"Question {i + 1}: Evaluation failed (0 points)")

        elif question["type"] == "code":
            prompt = f"""
            You are a strict technical interviewer evaluating code.
            
            Coding Question: {question["question"]}
            Submitted Code: {answers[i]}
            
            Evaluate for:
            1. Correctness
            2. Proper syntax
            3. Efficiency
            4. Error handling
            
            First line must be exactly "CORRECT" or "INCORRECT"
            Then provide specific technical feedback.
            """
            try:
                response = ollama.generate(
                    model="llama3.1",
                    prompt=prompt,
                )
                evaluation = response["response"].strip().split('\n')[0].upper()
                explanation = ' '.join(response["response"].strip().split('\n')[1:])
                
                if evaluation == "CORRECT":
                    score += 2
                    feedback.append(f"Question {i + 1}: Correct (2 points) - {explanation}")
                else:
                    feedback.append(f"Question {i + 1}: Incorrect (0 points) - {explanation}")
            except Exception as e:
                feedback.append(f"Question {i + 1}: Evaluation failed (0 points)")

    # Evaluate role-specific requirements (for internal use only)
    role_feedback = []
    for requirement in role_requirements["requirements"]:
        prompt = f"""
        You are a technical interviewer evaluating a candidate's suitability for the role of {role_requirements["role"]}.
        
        Requirement: {requirement}
        
        Based on the candidate's answers, does the candidate meet this requirement?
        First line must be exactly "YES" or "NO"
        Then provide a brief explanation of why.
        """
        try:
            response = ollama.generate(
                model="llama3.1",
                prompt=prompt,
            )
            evaluation = response["response"].strip().split('\n')[0].upper()
            explanation = ' '.join(response["response"].strip().split('\n')[1:])
            
            if evaluation == "YES":
                role_feedback.append(f"Requirement: {requirement} - Met (1 point) - {explanation}")
            else:
                role_feedback.append(f"Requirement: {requirement} - Not Met (0 points) - {explanation}")
        except Exception as e:
            role_feedback.append(f"Requirement: {requirement} - Evaluation failed (0 points)")

    return score, feedback, role_feedback

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
        if current_question["type"] == "text":
            answer = st.text_area("Your Answer", value=st.session_state.answers[st.session_state.current_question_index])
        elif current_question["type"] == "code":
            answer = st.text_area("Write your code here", value=st.session_state.answers[st.session_state.current_question_index])

        # Save the answer
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

    # Generate strengths and areas for improvement
    strengths = [
        "Strong coding skills in Python.",
        "Good understanding of database operations.",
    ]
    areas_for_improvement = [
        "Needs to improve theoretical knowledge of frameworks like Django.",
        "Should practice explaining complex concepts in detail.",
    ]

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
- **Technical Proficiency**: {technical_proficiency:.1f}/10 - The candidate demonstrates [summary].
- **Answer Quality**: {answer_quality:.1f}/10 - The candidate's answers were [summary].
- **Role Fit**: {role_fit:.1f}/10 - The candidate is [summary] for the role.
- **Recommendation**: {recommendation}

---

#### Detailed Evaluation:

##### 1. Technical Proficiency:
- **Rating**: {technical_proficiency:.1f}/10
- **Summary**: The candidate has [summary of technical skills based on experience and answers].

##### 2. Answer Quality:
- **Rating**: {answer_quality:.1f}/10
- **Summary**: The candidate provided [summary of answer quality and depth].

##### 3. Role Fit:
- **Rating**: {role_fit:.1f}/10
- **Summary**: The candidate is [summary of role fit].

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
Based on the assessment, the candidate is recommended for **[HIRE/NO HIRE]** due to [reason]. They should focus on [key areas for improvement] to enhance their technical proficiency and role fit.
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