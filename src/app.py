from fastapi import FastAPI

app = FastAPI(title='BeD')

@app.get('/')
def read_root():
    return {'message': 'Welcome to bed'}

