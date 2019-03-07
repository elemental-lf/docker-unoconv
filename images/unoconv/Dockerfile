FROM fedora:29 AS build

RUN dnf update -q -y && \
    dnf install -q -y rpm-build rpmdevtools asciidoc xmlto make git && \
    rpmdev-setuptree

ADD rpmbuild /root/rpmbuild

RUN find /root/rpmbuild -ls && rpmbuild -bb /root/rpmbuild/SPECS/unoconv.spec

FROM fedora:29 AS run

ARG CELERY_VERSION=4.3.0rc2
ARG BOTO3_VERSION=1.9.91

COPY --from=build /root/rpmbuild/RPMS/ /tmp/RPMS/

RUN dnf update -q -y && \
    dnf install -q -y python3 python3-pip python3-setuptools dumb-init && \
    dnf install  -y $(rpm -q --suggests /tmp/RPMS/*/*) && \
    dnf install  -y /tmp/RPMS/*/* && \
    dnf clean -y all && \
    pip3 install "celery==${CELERY_VERSION}" "boto3==${BOTO3_VERSION}"

# Add runtime user
RUN groupadd -r -g 1000 runtime && \
    useradd -r -g runtime -u 1000 -d /home/runtime runtime && \
    mkdir /home/runtime && \
    chown runtime:runtime /home/runtime && \
    chmod 770 /home/runtime

# LibreOffice needs a home directory
ENV HOME /home/runtime

ADD celery_unoconv/ /celery-worker/lib/celery_unoconv/
RUN mkdir /celery-worker/config && \
    mv /celery-worker/lib/celery_unoconv/celeryconfig.py /celery-worker/config && \
    ln -s ../../config/celeryconfig.py /celery-worker/lib/celery_unoconv/celeryconfig.py
ADD docker-entrypoint.sh /

USER 1000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ['help']
