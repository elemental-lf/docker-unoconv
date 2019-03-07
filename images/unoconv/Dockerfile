FROM fedora:29 AS build

RUN dnf update -q -y && \
    dnf install -q -y rpm-build rpmdevtools asciidoc xmlto make git && \
    rpmdev-setuptree

ADD rpmbuild /root/rpmbuild

RUN find /root/rpmbuild -ls && rpmbuild -bb /root/rpmbuild/SPECS/unoconv.spec

FROM fedora:29 AS run

COPY --from=build /root/rpmbuild/RPMS/ /tmp/RPMS/
ADD requirements.txt /tmp/requirements.txt

RUN dnf update -q -y && \
    dnf install -q -y python3 python3-pip python3-setuptools dumb-init && \
    dnf install  -y $(rpm -q --suggests /tmp/RPMS/*/*) && \
    dnf install  -y /tmp/RPMS/*/* && \
    dnf clean -y all && \
    pip3 install -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

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
