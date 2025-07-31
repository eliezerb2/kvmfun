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
  command: ['sh', '-c']
  # TODO: Consider using ssh-keyscan to add the host key to a known_hosts file instead of StrictHostKeyChecking
  args:
    - |
      set -ex
      echo "INFO: Starting ssh-setup init container"
      SSH_PATH="/appuser/.ssh"
      KEY_FILE="$SSH_PATH/id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}"
      CONFIG_FILE="$SSH_PATH/config"

      echo "INFO: Creating SSH directory: $SSH_PATH"
      mkdir -p "$SSH_PATH"
      chmod 700 "$SSH_PATH"

      echo "INFO: Copying private key from /secrets to $KEY_FILE"
      cp "/secrets/id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}" "$KEY_FILE"
      chmod 600 "$KEY_FILE"

      echo "INFO: Creating SSH config file $CONFIG_FILE to disable host key checking."
      cat << EOF > "$CONFIG_FILE"
      Host *
        StrictHostKeyChecking no
        UserKnownHostsFile /dev/null
        IdentityFile $KEY_FILE
      EOF
      chmod 600 "$CONFIG_FILE"

      echo "INFO: Verifying .ssh directory contents:"
      ls -la "$SSH_PATH"
      echo "INFO: ssh-setup init container finished successfully."
  volumeMounts:
    - name: ssh-secret
      mountPath: /secrets
    - name: ssh-key-volume
      mountPath: /root/.ssh
{{- end -}}

{{/*
Common volumeMounts for the main container.
*/}}
{{- define "kvmfun.pod.volumeMounts" -}}
- name: ssh-key-volume
  mountPath: /root/.ssh
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