# Step 1: Import the necessary libraries
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# Step 2: Load the dataset
data = pd.read_csv('customer_churn.csv')

X = data.drop('churn', axis=1)  # Features
y = data['churn']               # Target

# Step 3: Split the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 4: Build and train the logistic regression model
model = LogisticRegression(solver='liblinear')  # Initialize the logistic regression model
model.fit(X_train, y_train)  # Train the model using the training data

# Step 5: Make predictions on the test set
y_pred = model.predict(X_test)  # Predict the labels for the test data

# Step 6: Output the predictions alongside the true labels
results = pd.DataFrame({'True Labels': y_test, 'Predicted Labels': y_pred})

#  Testing the model on a single data point
single_data_point = pd.DataFrame({'monthly_spend': [80], 'contract_length': [12], 'support_calls': [15]})
single_prediction = model.predict(single_data_point)

print(f'Prediction for monthly_spend=80 and contract_length=12 and support_calls=15: {"Churn" if single_prediction[0] == 1 else "No Churn"}')

#  Testing the model on a single data point
single_data_point = pd.DataFrame({'monthly_spend': [5], 'contract_length': [12], 'support_calls': [1]})
single_prediction = model.predict(single_data_point)

print(f'Prediction for monthly_spend=5 and contract_length=12 and support_calls=1: {"Churn" if single_prediction[0] == 1 else "No Churn"}')

# Calculate and print the evaluation metrics
accuracy = accuracy_score(y_test, y_pred)
print(f'Accuracy: {accuracy * 100:.2f}%')