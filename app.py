import os
import streamlit as st
import ollama
import json
import csv
from datetime import datetime


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

# Function to generate responses using Ollama
# Function to generate responses using Ollama
def generate_response(prompt):
    try:
        response = ollama.generate(
            model="llama3.1",  # You can use other models like "llama3" or "mistral"
            prompt=prompt,
        )
        return response["response"]
    except Exception as e:
        return f"Error generating response: {str(e)}"

def generate_technical_questions(tech_stack):
    """
    Generates 3-5 technical questions based on the candidate's tech stack.
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


# Function to evaluate answers and calculate score
def evaluate_answers(questions, answers):
    """
    Strictly evaluates the candidate's answers and calculates a score.
    Points are only awarded for correct answers.
    """
    score = 0
    feedback = []

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

    return score, feedback



# Function to save data to CSV
def save_to_csv(candidate_info, questions, answers, score, feedback):
    """
    Saves interview data to a CSV file
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = "interview_responses.csv"
    
    # Prepare the data row
    row_data = {
        'Timestamp': timestamp,
        'Full Name': candidate_info['full_name'],
        'Email': candidate_info['email'],
        'Phone': candidate_info['phone'],
        'Years of Experience': candidate_info['years_of_experience'],
        'Desired Position': candidate_info['desired_position'],
        'Current Location': candidate_info['current_location'],
        'Tech Stack': ', '.join(candidate_info['tech_stack']),
        'Total Score': score
    }
    
    # Add questions and answers
    for i, (question, answer) in enumerate(zip(questions, answers)):
        row_data[f'Question_{i+1}'] = question['question']
        row_data[f'Answer_{i+1}'] = answer
        row_data[f'Feedback_{i+1}'] = feedback[i]
    
    # Check if file exists to write headers
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(row_data.keys()))
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row_data)



# Function to handle fallback mechanism
def fallback_response():
    """
    Provides a meaningful response when the chatbot does not understand the input.
    """
    return "I'm sorry, I didn't understand that. Could you please rephrase or ask something else?"

# Function to end the conversation gracefully
def end_conversation():
    """
    Gracefully concludes the conversation.
    """
    st.session_state.conversation_ended = True
    return "Thank you for your time! We will review your responses and get back to you shortly. Have a great day!"

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
        desired_position = st.text_input("Desired Position (e.g., Software Engineer, Data Scientist)")
        current_location = st.text_input("Current Location")
        tech_stack = st.multiselect(
            "Tech Stack (Select all that apply)",
            ["Python", "Java", "JavaScript", "Django", "React", "PostgreSQL", "AWS", "Machine Learning"]
        )
        submitted = st.form_submit_button("Submit")

        if submitted:
            # Save candidate information to session state
            st.session_state.candidate_info = {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "years_of_experience": years_of_experience,
                "desired_position": desired_position,
                "current_location": current_location,
                "tech_stack": tech_stack,
            }
            st.session_state.info_collected = True
            st.session_state.technical_questions = generate_technical_questions(tech_stack)
            if not st.session_state.technical_questions:
                st.error("Failed to generate technical questions. Please try again.")
                st.session_state.info_collected = False
            else:
                st.session_state.answers = [""] * len(st.session_state.technical_questions)
                st.rerun()  # Use st.rerun() instead of st.experimental_rerun()

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
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
        with col2:
            if st.session_state.current_question_index < len(st.session_state.technical_questions) - 1:
                if st.button("Next"):
                    st.session_state.current_question_index += 1
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
            else:
                if st.button("Submit Answers"):
                    st.session_state.submitted = True
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()

# Step 3: Evaluate Answers
if st.session_state.submitted and not st.session_state.conversation_ended:
    st.write("### Evaluation Results")
    score, feedback = evaluate_answers(st.session_state.technical_questions, st.session_state.answers)
    st.write(f"#### Your Score: {score}/{len(st.session_state.technical_questions) * 2}")

    for fb in feedback:
        st.write(fb)
        
    # Save responses to CSV
    save_to_csv(
        st.session_state.candidate_info,
        st.session_state.technical_questions,
        st.session_state.answers,
        score,
        feedback
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
            st.rerun()  # Restart the session
    with col2:
        if st.button("End Session"):
            st.session_state.conversation_ended = True
            st.write("Thank you for participating! Have a great day!")

# Step 4: Professional Discussion and Technical Guidance
def generate_candidate_report(candidate_info, questions, answers, score, chat_history):
    """
    Generates a detailed technical assessment report for the candidate
    """
    total_possible_score = len(questions) * 2
    score_percentage = (score / total_possible_score) * 100
    
    prompt = f"""
    Generate a strict technical assessment report for this candidate:

    CANDIDATE PROFILE:
    - Role: {candidate_info['desired_position']}
    - Experience: {candidate_info['years_of_experience']} years
    - Tech Stack: {', '.join(candidate_info['tech_stack'])}
    - Score: {score}/{total_possible_score} ({score_percentage:.1f}%)

    TECHNICAL ASSESSMENT:
    Questions and Answers:
    {' '.join([f'Q{i+1}: {q["question"]} | A: {a}' for i, (q, a) in enumerate(zip(questions, answers))])}

    Based on the above:
    1. Evaluate technical proficiency considering years of experience
    2. Analyze answer quality and depth
    3. Assess role fit
    4. Provide clear HIRE/NO HIRE recommendation
    5. List key strengths and areas for improvement

    Format the report professionally with clear sections and bullet points.
    Be strict and objective in evaluation.
    """
    
    report = generate_response(prompt)
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
        # Modify the Complete Interview Process button section:
        if st.button("Complete Interview Process"):
            st.session_state.conversation_ended = True
            
            # Generate and display report
            st.write("### Technical Assessment Report")
            report = generate_candidate_report(
                st.session_state.candidate_info,
                st.session_state.technical_questions,
                st.session_state.answers,
                score,
                st.session_state.chat_history
            )
            
            # Display report in a structured format
            st.markdown(report)
            
            # Save report to CSV along with other data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_data = {
                'Timestamp': timestamp,
                'Candidate_Name': st.session_state.candidate_info['full_name'],
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