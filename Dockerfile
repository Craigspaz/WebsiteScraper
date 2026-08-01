## Most of this file is from: https://medium.com/@kroeze.wb/running-selenium-in-aws-lambda-806c7e88ec64 / https://github.com/wbytedev/wbyte-selenium-lambda

FROM amazon/aws-lambda-python:3.13-x86_64

# install chrome dependencies
RUN dnf install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip

RUN dnf upgrade -y

COPY ./chrome-installer.sh ./chrome-installer.sh
RUN chmod +x ./chrome-installer.sh
RUN ./chrome-installer.sh
RUN rm ./chrome-installer.sh

RUN pip install selenium boto3 requests

COPY main.py ./

CMD [ "main.lambda_handler" ]
