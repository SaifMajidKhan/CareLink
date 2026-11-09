enum AccountRole {
  patient,
  caregiver;

  static AccountRole? fromApi(Object? value) => switch (value) {
    'patient' => AccountRole.patient,
    'caregiver' => AccountRole.caregiver,
    _ => null,
  };
}
