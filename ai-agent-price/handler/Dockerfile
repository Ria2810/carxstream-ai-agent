FROM public.ecr.aws/lambda/python:3.12

#COPY handler/. ./
COPY ./ ./

RUN python3.12 -m pip install -r requirements.txt

CMD ["lambda_trigger.lambda_handler"]