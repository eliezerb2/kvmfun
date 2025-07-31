{{/*
Common volumes for application and test pods.
*/}}
{{- define "kvmfun.pod.volumes" -}}
- name: ssh-key-volume
  emptyDir: {}
- name: ssh-secret
  secret:
    secretName: {{ .Values.sshSecretName }}
    defaultMode: 0400
    items:
      - key: id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}
        path: id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}
{{- end -}}

{{/*
Common initContainer for setting up SSH keys.
*/}}
{{- define "kvmfun.pod.initcontainer" -}}
- name: ssh-setup
  image: busybox
  # This init container runs as root to set up the .ssh directory.
  # It places the files in a shared volume and sets the correct ownership.
  command: ['sh', '-c']
  # TODO: Consider using ssh-keyscan to add the host key to a known_hosts file instead of StrictHostKeyChecking
  args:
    - |
      set -ex
      echo "INFO: Starting ssh-setup initContainer"
      # Path inside this initContainer where the shared volume is mounted
      INIT_CONTAINER_SSH_PATH="/mnt/ssh"
      # Final, absolute path where the volume will be mounted in the main container
      MAIN_CONTAINER_SSH_PATH="/home/appuser/.ssh"

      KEY_FILE_NAME="id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}"
      KEY_FILE_IN_INIT="$INIT_CONTAINER_SSH_PATH/$KEY_FILE_NAME"
      KEY_FILE_IN_MAIN="$MAIN_CONTAINER_SSH_PATH/$KEY_FILE_NAME"
      CONFIG_FILE_IN_INIT="$INIT_CONTAINER_SSH_PATH/config"

      echo "INFO: Creating SSH directory: $INIT_CONTAINER_SSH_PATH"
      mkdir -p "$INIT_CONTAINER_SSH_PATH"
      chmod 700 "$INIT_CONTAINER_SSH_PATH"

      echo "INFO: Copying private key from /secrets to $KEY_FILE_IN_INIT"
      cp "/secrets/$KEY_FILE_NAME" "$KEY_FILE_IN_INIT"
      chmod 600 "$KEY_FILE_IN_INIT"

      echo "INFO: Creating SSH config file $CONFIG_FILE_IN_INIT with correct path for main container."
      cat << EOF > "$CONFIG_FILE_IN_INIT"
      Host *
        StrictHostKeyChecking no
        UserKnownHostsFile /dev/null
        IdentityFile $KEY_FILE_IN_MAIN
      EOF
      chmod 600 "$CONFIG_FILE_IN_INIT"

      echo "INFO: Verifying .ssh directory contents:"
      ls -laR "$INIT_CONTAINER_SSH_PATH"

      # The 'appuser' in the Dockerfile is created with 'useradd -r', which on the
      # python:3.11.7-slim base image assigns UID 999 and GID 999.
      # We must change ownership of the files so the non-root main container can use them.
      echo "INFO: Changing ownership to appuser (999:999)"
      chown -R 999:999 "$INIT_CONTAINER_SSH_PATH"

      echo "INFO: Verifying final permissions:"
      ls -laR "$INIT_CONTAINER_SSH_PATH"
      echo "INFO: ssh-setup init container finished successfully."
  volumeMounts:
    - name: ssh-secret
      mountPath: /secrets
    - name: ssh-key-volume
      mountPath: /mnt/ssh
{{- end -}}

{{/*
Common volumeMounts for the main container.
*/}}
{{- define "kvmfun.pod.volumeMounts" -}}
- name: ssh-key-volume
  # Mount the prepared volume into the appuser's actual home directory.
  mountPath: /home/appuser/.ssh
  readOnly: true
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "kvmfun.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{- .Values.serviceAccount.name | default (include "kvmfun.fullname" .) -}}
{{- else -}}
    {{- .Values.serviceAccount.name | default "default" -}}
{{- end -}}
{{- end -}}