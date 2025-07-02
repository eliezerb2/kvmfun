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
  command: ['sh', '-c',
    'mkdir -p /root/.ssh &&
     cp /secrets/id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }} /root/.ssh/id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }} &&
     chmod 600 /root/.ssh/* &&
     echo "Host *" > /root/.ssh/config &&
     echo "  StrictHostKeyChecking no" >> /root/.ssh/config &&
     echo "  UserKnownHostsFile /dev/null" >> /root/.ssh/config &&
     echo "  IdentityFile /root/.ssh/id_{{ .Values.appConfig.LIBVIRT_SSH_KEY_TYPE }}" >> /root/.ssh/config &&
     chmod 600 /root/.ssh/config']
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