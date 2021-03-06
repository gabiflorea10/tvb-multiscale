#
# TVB & NEST simulations environment
#
# Install Python 3, NEST, then tvb packages
#

FROM neurodebian:buster
MAINTAINER lia.domide@codemart.ro

ENV DEBIAN_FRONTEND noninteractive
ENV LANG=C.UTF-8

RUN apt-get update; apt-get install -y automake libtool build-essential openmpi-bin libopenmpi-dev git vim octave \
                       wget python3.7 libpython3.7 libpython3-dev libncurses5-dev libreadline-dev libgsl0-dev cython3 \
                       python3.7-dev python3-pip python3-numpy python3-scipy python3-matplotlib python3-nose \
                       python3-venv python-virtualenv python3-pyqt5 python-dev libgsl-dev libncurses-dev \
                       subversion python3-mpi4py cmake zip unzip; \
    apt-get clean

# Create user different than root
RUN useradd -ms /bin/bash docker
USER docker
ARG HOME=/home/docker

# Create a dedicated Python env for working in it
ENV VENV=$HOME/env/neurosci
RUN mkdir $HOME/env; mkdir $HOME/packages
RUN python3 -m venv $VENV && python3 -m venv --system-site-packages $VENV; \
    $VENV/bin/pip3 install --upgrade pip; \
    $VENV/bin/pip3 install parameters quantities neo "django<1.9" django-tagging future hgapi gitpython sumatra nixio; \
    $VENV/bin/pip3 install pandas jupyterlab nodejs pytest pytest-cov pytest-benchmark oct2py scikit-learn scipy xarray; \
    $VENV/bin/pip3 install --ignore-installed entrypoints; \
    $VENV/bin/pip3 install --upgrade nose
# django<1.9 is needed for pynest - september 2019 - NEST 2.18

# Install from sources libneurosim (NEST boost dependency)
WORKDIR $HOME/packages
RUN git clone --depth 1 https://github.com/INCF/libneurosim.git; \
    cd libneurosim; ./autogen.sh
RUN mkdir $VENV/build
WORKDIR $VENV/build
RUN mkdir libneurosim; \
    cd libneurosim; \
    PYTHON=$VENV/bin/python $HOME/packages/libneurosim/configure --prefix=$VENV; \
    make; make install; ls $VENV/lib $VENV/include; \
    ln -s /usr/lib/python3.7/config-x86_64-linux-gnu/libpython3.7.so $VENV/lib/

# Install NEST, latest stable version (July 2019)
ARG NEST_VER=2.18.0
ARG NEST=nest-simulator-$NEST_VER
ARG NEST_SRC=$HOME/packages/$NEST
ENV NEST_INSTALL_DIR=$VENV/nest_build
ENV NEST_PYTHON_PREFIX=${NEST_INSTALL_DIR}/lib/python3.7/site-packages
ENV NEST_MODULE_PATH=${NEST_INSTALL_DIR}/lib/nest

WORKDIR $HOME/packages
RUN wget  https://github.com/nest/nest-simulator/archive/v$NEST_VER.tar.gz -O $HOME/packages/$NEST.tar.gz; \
    tar xzf $NEST.tar.gz; rm $NEST.tar.gz; \
    cd $NEST; \
    cmake -DCMAKE_INSTALL_PREFIX=${NEST_INSTALL_DIR} \
          -Dwith-mpi=ON  \
          -Dwith-python=3 \
          ###-Dwith-music=ON \
          -Dwith-libneurosim=$VENV \
          -DPYTHON_LIBRARY=/usr/lib \
          -DPYTHON_INCLUDE_DIR=/usr/include/python3.7m \
          ${NEST_SRC}; \
    make; make install

# Install nestml
RUN $VENV/bin/pip3 install setuptools; \
    git clone --depth 1 https://github.com/nest/nestml.git; \
    cd nestml; \
    $VENV/bin/python setup.py install

# Install TVB specific packages
WORKDIR $HOME/packages

RUN wget https://zenodo.org/record/3497545/files/tvb_data_2_0_1.zip?download=1 -O tvb_data.zip; \
    unzip tvb_data.zip; rm tvb_data.zip; \
    cd tvb_data; \
    $VENV/bin/python setup.py develop

RUN git clone --depth 1 https://github.com/the-virtual-brain/tvb-root.git; \
    cd tvb-root/scientific_library; \
    $VENV/bin/python setup.py develop;

RUN git clone --depth 1 https://github.com/the-virtual-brain/tvb-multiscale.git; \
    cd tvb-multiscale; \
    $VENV/bin/python setup.py develop --no-deps

# Activate the right env:
ENV PYTHONPATH=$PYTHONPATH:$VENV:${NEST_PYTHON_PREFIX}
ENV NEST_DATA_DIR=${NEST_INSTALL_DIR}/share/nest
ENV NEST_DOC_DIR=${NEST_INSTALL_DIR}/share/doc/nest
ENV SLI_PATH=${NEST_INSTALL_DIR}/share/nest/sli
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${NEST_MODULE_PATH}
RUN echo "source ${VENV}/bin/activate" >> /home/docker/.bashrc

## Run the following lines in case you want to install your own NEST module with NEST models
#ENV MYMODULES_DIR=$HOME/packages/tvb-multiscale/tvb_nest/nest/modules
#ENV MYMODULES_BLD_DIR=$HOME/packages/nest_modules_builds
#RUN cp -r ${MYMODULES_DIR} ${MYMODULES_BLD_DIR}
#COPY . tvb-multiscale/
#ARG MYMODULES_LIST="tvb_rate_wongwang iaf_cond_deco2014"
#ARG MYMODULES_DIR=$HOME/packages/tvb-multiscale/tvb_nest/nest/modules
#ARG NEST_CONFIG=${NEST_INSTALL_DIR}/bin/nest-config
#RUN for MYMODULE_NAME in $MYMODULES_LIST; do export MYMODULE_DIR=${MYMODULES_DIR}/${MYMODULE_NAME}; \
#        export MYMODULE_BLD=${MYMODULES_BLD_DIR}/${MYMODULE_NAME}module_bld; \
#        mkdir -p ${MYMODULE_BLD}; cd ${MYMODULE_BLD}; \
#            cmake -Dwith-nest=$NEST_CONFIG ${MYMODULE_DIR}; \
#            make; make install; \
#    done

# Final configurations
# tvb42
RUN $VENV/bin/jupyter notebook --generate-config; \
    echo "c.NotebookApp.password='sha1:12bff019c253:9daecd92c2e9bdb10b3b8a06767a74a0fe078d7c'">>/home/docker/.jupyter/jupyter_notebook_config.py

WORKDIR /home/docker/
COPY docker/installation_test.py /home/docker/

# For running tests
#CMD $VENV/bin/pytest /home/docker/packages/tvb-multiscale/tvb_nest/tests

# CMD cd /home/docker/packages/nestml; $VENV/bin/pytest setup.py test
# CMD $VENV/bin/python -c "import pyNN.nest as sim; sim.setup(); sim.end(); print(sim)";
# CMD $VENV/bin/python /home/docker/packages/tvb-multiscale/docker/installation_test.py
# CMD cd /home/docker/packages/tvb-multiscale; $VENV/bin/pytest tvb_nest/tests
# CMD $VENV/bin/python /home/docker/packages/tvb-multiscale/tvb_nest/examples/red_ww_exc_io_inh_i.py
# CMD /bin/bash

CMD $VENV/bin/jupyter notebook --ip 0.0.0.0 --no-browser --allow-root