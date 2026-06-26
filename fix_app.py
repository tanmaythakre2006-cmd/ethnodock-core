with open('app.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('                st.subheader("Stream A: Verified'):
        # Fix indentation to be outside the `with st.status` block
        pass
